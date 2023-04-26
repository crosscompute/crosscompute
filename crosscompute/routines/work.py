# TODO: Consider giving scripts access to CROSSCOMPUTE_ROOT_URI
import shlex
import subprocess
from collections import defaultdict
from concurrent.futures import (
    ProcessPoolExecutor, ThreadPoolExecutor, as_completed)
from contextlib import contextmanager
from logging import getLogger
from os import environ, getenv, symlink
from os.path import relpath
from random import choice
from threading import Thread
from time import sleep, time
from urllib.error import URLError
from urllib.request import urlretrieve as download_uri

import requests
from invisibleroads_macros_disk import make_folder
from invisibleroads_macros_web.port import find_open_port
from jinja2 import Template

from ..constants import (
    Error,
    Info,
    Task,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    MAXIMUM_PORT,
    MINIMUM_PORT,
    PORT_ROUTE,
    PROXY_URI,
    STEP_CODE_BY_NAME,
    STEP_NAMES)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeDataError,
    CrossComputeExecutionError,
    CrossComputeError)
from ..macros.iterable import find_item, group_by
from .configuration import (
    get_folder_plus_path)
from .printer import (
    print_batch)
from .uri import (
    get_automation_slug,
    get_batch_slug)
from .variable import (
    get_variable_data_by_id,
    get_variable_value_by_id,
    process_variable_data,
    save_variable_data,
    update_variable_data)


class AbstractEngine():

    def __init__(self, with_rebuild=True):
        self.with_rebuild = with_rebuild

    def run_batch(
            self, automation_definition, batch_definition, user_environment):
        reference_time = time()
        batch_folder, batch_environment = prepare_batch(
            automation_definition, batch_definition)
        if not automation_definition.script_definitions:
            return
        batch_identifier = ' '.join([
            automation_definition.name, automation_definition.version,
            str(batch_folder)])
        L.info('%s running', batch_identifier)
        try:
            return_code = self.run(
                automation_definition, batch_folder,
                batch_environment | user_environment)
        except CrossComputeConfigurationError as e:
            e.automation_definition = automation_definition
            raise
        except CrossComputeExecutionError as e:
            e.automation_definition = automation_definition
            return_code = e.code
            L.error('%s failed; %s', batch_identifier, e)
        except KeyboardInterrupt:
            return_code = Error.COMMAND_INTERRUPTED
            L.error('%s interrupted')
        else:
            L.info('%s done', batch_identifier)
        return _process_batch(automation_definition, batch_definition, [
            'output', 'log', 'debug',
        ], {'debug': {
            'source_time': reference_time,
            'execution_time_in_seconds': time() - reference_time,
            'return_code': return_code}})

    def prepare(self, automation_definition):
        for s in automation_definition.script_definitions:
            s.get_command_string()


class UnsafeEngine(AbstractEngine):

    def run(self, automation_definition, batch_folder, custom_environment):
        step_folder_by_name = _get_step_folder_by_name(
            automation_definition.folder, batch_folder)
        script_definitions = automation_definition.script_definitions
        script_environment = _prepare_script_environment(
            step_folder_by_name, custom_environment, with_path=True)
        debug_folder = step_folder_by_name['debug_folder']
        o_path = debug_folder / 'stdout.txt'
        e_path = debug_folder / 'stderr.txt'
        with open(o_path, 'wt') as o_file, open(e_path, 'w+t') as e_file:
            for script_definition in script_definitions:
                return_code = _run_script(
                    script_definition, step_folder_by_name,
                    script_environment, o_file, e_file)
        return return_code


class PodmanEngine(AbstractEngine):

    def prepare(self, automation_definition):
        if not automation_definition.script_definitions:
            return
        image_name = _get_image_name(automation_definition)
        if not self.with_rebuild and _has_podman_image(image_name):
            return
        automation_folder = automation_definition.folder
        (automation_folder / CONTAINER_FILE_NAME).write_text(
            _prepare_container_file_text(automation_definition))
        (automation_folder / '.containerignore').write_text(
            CONTAINER_IGNORE_TEXT)
        command_texts = [
            s.get_command_string().format(**CONTAINER_STEP_FOLDER_BY_NAME)
            for s in automation_definition.script_definitions]
        (automation_folder / CONTAINER_SCRIPT_NAME).write_text(
            '\n'.join([_ + CONTAINER_PIPE_TEXT for _ in command_texts]))
        if subprocess.run([
            'podman', 'build', '-t', image_name, '-f', CONTAINER_FILE_NAME,
        ], cwd=automation_folder).returncode != 0:
            raise CrossComputeExecutionError(f'could not build "{image_name}"')

    def run(self, automation_definition, batch_folder, custom_environment):
        automation_folder = automation_definition.folder
        absolute_batch_folder = automation_folder / batch_folder
        container_id, port_packs = _run_podman_image(
            automation_definition, batch_folder, custom_environment)
        try:
            with _proxy_podman_ports(
                    automation_definition, batch_folder, custom_environment,
                    port_packs):
                _copy_datasets_into_podman(container_id, automation_definition)
                _set_podman_folder_owner(absolute_batch_folder, 1000)
                return_code = _run_podman_command({'cwd': automation_folder}, [
                    'exec', '--env-file', CONTAINER_ENV_NAME, container_id,
                    'bash', CONTAINER_SCRIPT_NAME]).returncode
        except KeyboardInterrupt:
            return_code = Error.COMMAND_INTERRUPTED
        except Exception:
            raise
        finally:
            _set_podman_folder_owner(absolute_batch_folder, 0)
            _run_podman_command({}, ['kill', container_id])
        return _process_podman_return_code(return_code, absolute_batch_folder)


def run_automation(automation_definition, user_environment, with_rebuild=True):
    ds = []
    run_batch = get_script_engine(
        automation_definition.engine_name, with_rebuild).run_batch
    concurrency_name = automation_definition.batch_concurrency_name
    update_datasets(automation_definition)
    try:
        if concurrency_name == 'single':
            ds.extend(_run_automation_single(
                automation_definition, run_batch, user_environment))
        else:
            ds.extend(_run_automation_multiple(
                automation_definition, run_batch, user_environment,
                concurrency_name))
    except CrossComputeError as e:
        e.automation_definition = automation_definition
        L.error(e)
    return ds


def run_batch(automation_definition, batch_definition, user_environment):
    engine = get_script_engine(
        automation_definition.engine_name, with_rebuild=False)
    update_datasets(automation_definition)
    engine.run_batch(
        automation_definition, batch_definition, user_environment)


def get_script_engine(engine_name, with_rebuild=True):
    try:
        ScriptEngine = {
            'unsafe': UnsafeEngine,
            'podman': PodmanEngine,
        }[engine_name]
    except KeyError:
        raise CrossComputeExecutionError(f'unsupported engine "{engine_name}"')
    return ScriptEngine(with_rebuild=with_rebuild)


def update_datasets(automation_definition):
    automation_folder = automation_definition.folder
    for dataset_definition in automation_definition.dataset_definitions:
        target_path = automation_folder / dataset_definition.path
        target_folder = make_folder(target_path.parent)
        reference_configuration = dataset_definition.reference
        reference_path = get_folder_plus_path(reference_configuration)
        if reference_path:
            source_path = automation_folder / reference_path
            if target_path.is_symlink():
                if target_path.resolve() == source_path.resolve():
                    continue
                target_path.unlink()
            elif target_path.exists():
                continue
            symlink(relpath(source_path, target_folder), target_path)
        elif 'uri' in reference_configuration:
            reference_uri = reference_configuration['uri']
            try:
                download_uri(reference_uri, target_path)
            except URLError:
                L.error(f'could not download dataset from {reference_uri}')


def process_loop(
        automation_definitions, automation_tasks, live_uris, file_changes,
        user_environment, server_uri, with_rebuild):
    for a in automation_definitions:
        prepare_automation(a, with_rebuild)
        for b in a.batch_definitions:
            prepare_batch(a, b)
    try:
        while True:
            sleep(1)
            try:
                automation_task = _get_automation_task(
                    automation_tasks, automation_definitions, live_uris,
                    file_changes, user_environment)
            except IndexError:
                continue
            thread = Thread(
                target=_process_task, args=automation_task + (server_uri,),
                daemon=True)
            thread.start()
    except KeyboardInterrupt:
        pass


def prepare_automation(automation_definition, with_rebuild=True):
    engine = get_script_engine(automation_definition.engine_name, with_rebuild)
    engine.prepare(automation_definition)


def prepare_batch(automation_definition, batch_definition):
    variable_definitions = automation_definition.get_variable_definitions(
        'input')
    variable_definitions_by_path = group_by(variable_definitions, 'path')
    data_by_id = batch_definition.data_by_id
    batch_folder = batch_definition.folder
    batch_environment = _prepare_batch_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    step_folder_by_name = _make_step_folder_by_name(
        automation_definition.folder, batch_folder)
    if not data_by_id:
        return batch_folder, batch_environment
    input_folder = step_folder_by_name['input_folder']
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = input_folder / path
        save_variable_data(input_path, data_by_id, variable_definitions)
    return batch_folder, batch_environment


def _run_automation_single(automation_definition, run_batch, user_environment):
    ds = []
    for batch_definition in automation_definition.batch_definitions:
        ds.append(run_batch(
            automation_definition, batch_definition, user_environment))
    return ds


def _run_automation_multiple(
        automation_definition, run_batch, user_environment, concurrency_name):
    ds = []
    if concurrency_name == 'thread':
        BatchExecutor = ThreadPoolExecutor
    else:
        BatchExecutor = ProcessPoolExecutor
    with BatchExecutor() as executor:
        futures = []
        for batch_definition in automation_definition.batch_definitions:
            futures.append(executor.submit(
                run_batch, automation_definition, batch_definition,
                user_environment))
        try:
            for future in as_completed(futures):
                ds.append(future.result())
        except KeyboardInterrupt:
            pass
    return ds


def _get_automation_task(
        automation_tasks, automation_definitions, live_uris, file_changes,
        user_environment):
    if automation_tasks:
        return automation_tasks.pop(0)
    automation_definition = None
    if live_uris:
        try:
            automation_definition, batch_definition = _get_automation_pack(
                automation_definitions, choice(live_uris))
        except IndexError:
            pass
        if automation_definition:
            task_mode = _get_task_mode(
                automation_definition, batch_definition, file_changes)
            if task_mode is None:
                automation_definition = None
    if not automation_definition:
        selected_automation_definitions = [
            _ for _ in automation_definitions if _.is_interval_strict]
        if selected_automation_definitions:
            automation_definition = choice(selected_automation_definitions)
            batch_definition = choice(automation_definition.batch_definitions)
            if automation_definition.is_interval_ready(batch_definition):
                task_mode = Task.RUN_PRINT
            else:
                automation_definition = None
    if automation_definition:
        batch_clock = batch_definition.clock
        if batch_clock.is_in('run') or batch_clock.is_in('print'):
            automation_definition = None
    if not automation_definition:
        raise IndexError
    return automation_definition, batch_definition, user_environment, task_mode


def _get_automation_pack(automation_definitions, reference_uri):
    automation_slug = get_automation_slug(reference_uri)
    if not automation_slug:
        raise IndexError
    try:
        automation_definition = find_item(
            automation_definitions, 'slug', automation_slug,
            normalize=str.casefold)
    except StopIteration:
        raise IndexError
    batch_slug = get_batch_slug(reference_uri)
    if batch_slug:
        try:
            batch_definition = find_item(
                automation_definition.batch_definitions, 'slug', batch_slug)
        except StopIteration:
            raise IndexError
    else:
        batch_definition = automation_definition.batch_definitions[0]
    return automation_definition, batch_definition


def _get_task_mode(automation_definition, batch_definition, file_changes):
    batch_clock = batch_definition.clock
    run_time = batch_clock.get_start_time('run')
    if not run_time:
        return Task.RUN_PRINT
    print_time = batch_clock.get_start_time('print')
    for t, infos in file_changes.items():
        if t < run_time:
            continue
        for info in infos:
            match info['code']:
                case Info.VARIABLE:
                    if info['step'] != 'i' or batch_clock.is_in('run', t):
                        continue
                    return Task.RUN_PRINT
                case Info.SCRIPT:
                    try:
                        automation_definition.script_definitions[
                            info['index']].command = None
                    except AttributeError:
                        pass
                    return Task.RUN_PRINT
                case Info.DATASET:
                    return Task.RUN_PRINT
        if t < print_time:
            continue
        for info in infos:
            if info['code'] in [Info.STYLE, Info.TEMPLATE]:
                return Task.PRINT_ONLY
    if automation_definition.is_interval_ready(batch_definition):
        return Task.RUN_PRINT


def _process_task(
        automation_definition, batch_definition, user_environment, task_mode,
        server_uri):
    batch_clock = batch_definition.clock
    try:
        if task_mode == Task.RUN_PRINT:
            with batch_clock.time('run'):
                run_batch(
                    automation_definition, batch_definition, user_environment)
        with batch_clock.time('print'):
            print_batch(
                automation_definition, batch_definition, server_uri,
                is_draft=True)
    except CrossComputeError as e:
        e.automation_definition = automation_definition
        L.error(e)
    except KeyboardInterrupt:
        pass


def _prepare_batch_environment(
        automation_definition, variable_definitions, data_by_id):
    batch_environment = {}
    for variable_id in automation_definition.environment_variable_ids:
        batch_environment[variable_id] = environ[variable_id]
    for variable_id in (_.id for _ in variable_definitions):
        if variable_id in data_by_id:
            continue
        try:
            batch_environment[variable_id] = environ[variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'{variable_id} is missing in the environment')
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id, with_exceptions=False)
    variable_value_by_id = get_variable_value_by_id(variable_data_by_id)
    return batch_environment | variable_value_by_id


def _prepare_script_environment(
        step_folder_by_name, custom_environment, with_path=False):
    script_environment = custom_environment | {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in step_folder_by_name.items()}
    if with_path:
        script_environment['PATH'] = getenv('PATH', '')
    return script_environment


def _make_step_folder_by_name(automation_folder, batch_folder):
    step_folder_by_name = _get_step_folder_by_name(
        automation_folder, batch_folder)
    for folder in step_folder_by_name.values():
        folder.mkdir(parents=True, exist_ok=True)
    return step_folder_by_name


def _get_step_folder_by_name(automation_folder, batch_folder):
    return {
        _ + '_folder': automation_folder / batch_folder / _
        for _ in STEP_NAMES}


def _run_script(
        script_definition, step_folder_by_name, script_environment,
        stdout_file, stderr_file):
    command_string = script_definition.get_command_string()
    if not command_string:
        return
    command_text = command_string.format(**step_folder_by_name)
    automation_folder = script_definition.automation_folder
    script_folder = script_definition.folder
    command_folder = automation_folder / script_folder
    return _run_command(
        command_text, command_folder, script_environment, stdout_file,
        stderr_file)


def _run_command(
        command_string, command_folder, script_environment, o_file, e_file):
    try:
        process = subprocess.run(
            shlex.split(command_string),
            check=True,
            cwd=command_folder,
            env=script_environment,
            stdout=o_file,
            stderr=e_file)
    except (IndexError, OSError):
        error = CrossComputeConfigurationError(
            f'could not run {shlex.quote(command_string)} in {command_folder}')
        error.code = Error.COMMAND_NOT_RUNNABLE
        raise error
    except subprocess.CalledProcessError as e:
        e_file.seek(0)
        error = CrossComputeExecutionError(e_file.read().rstrip())
        error.code = e.returncode
        raise error
    return process.returncode


def _process_batch(
        automation_definition, batch_definition, step_names,
        extra_data_by_id_by_step_name):
    variable_data_by_id_by_step_name = {}
    automation_folder = automation_definition.folder
    batch_folder = batch_definition.folder
    for step_name in step_names:
        variable_data_by_id_by_step_name[step_name] = variable_data_by_id = {}
        extra_data_by_id = extra_data_by_id_by_step_name.get(step_name, {})
        step_folder = automation_folder / batch_folder / step_name
        variable_definitions = automation_definition.get_variable_definitions(
            step_name)
        for variable_definition in variable_definitions:
            variable_id = variable_definition.id
            variable_path = variable_definition.path
            if variable_id in extra_data_by_id:
                continue
            path = step_folder / variable_path
            try:
                variable_data = process_variable_data(
                    path, variable_definition)
            except CrossComputeDataError as e:
                e.automation_definition = automation_definition
                L.error(e)
                continue
            variable_data_by_id[variable_id] = variable_data
        if extra_data_by_id:
            update_variable_data(
                step_folder / 'variables.dictionary', extra_data_by_id)
            variable_data_by_id.update(extra_data_by_id)
    return variable_data_by_id_by_step_name


def _prepare_container_file_text(automation_definition):
    path_folders = set()
    package_ids_by_manager_name = defaultdict(set)
    for package_definition in automation_definition.package_definitions:
        manager_name = package_definition.manager_name
        package_ids_by_manager_name[manager_name].add(package_definition.id)
    root_package_commands, user_package_commands = [], []
    if 'apt' in package_ids_by_manager_name:
        s = ' '.join(sorted(package_ids_by_manager_name['apt']))
        root_package_commands.append(
            f'apt update && apt -y install {s} && apt clean')
    if 'dnf' in package_ids_by_manager_name:
        s = ' '.join(sorted(package_ids_by_manager_name['dnf']))
        root_package_commands.append(
            f'dnf -y install {s} && dnf clean all')
    if 'npm' in package_ids_by_manager_name:
        s = ' '.join(sorted(package_ids_by_manager_name['npm']))
        user_package_commands.append(
            f'npm install {s} --prefix ~/.local -g && '
            f'npm cache clean --force')
        path_folders.add('/home/user/.local/bin')
    if 'pip' in package_ids_by_manager_name:
        s = ' '.join(sorted(package_ids_by_manager_name['pip']))
        user_package_commands.append(
            f'pip install {s} --user && '
            f'pip cache purge && rm -rf ~/.cache')
        path_folders.add('/home/user/.local/bin')
    return CONTAINER_FILE_TEXT.render(
        parent_image_name=automation_definition.parent_image_name,
        root_package_commands=root_package_commands,
        user_package_commands=user_package_commands,
        path_folders=path_folders,
        port_numbers=[str(
            _.number) for _ in automation_definition.port_definitions])


def _has_podman_image(image_name):
    return _run_podman_command({}, [
        'image', 'exists', image_name]).returncode == 0


def _run_podman_image(automation_definition, batch_folder, custom_environment):
    automation_folder = automation_definition.folder
    container_env_path = automation_folder / CONTAINER_ENV_NAME
    script_environment = _prepare_script_environment(
        CONTAINER_STEP_FOLDER_BY_NAME, custom_environment, with_path=False)
    container_env_path.write_text('\n'.join(
        f'{k}={v}' for k, v in script_environment.items()))
    port_definitions = automation_definition.port_definitions
    image_name = _get_image_name(automation_definition)
    absolute_batch_folder = automation_folder / batch_folder
    while True:
        port_packs = []
        command_terms = []
        for port_definition in port_definitions:
            port_id = port_definition.id
            host_port = find_open_port(
                minimum_port=MINIMUM_PORT,
                maximum_port=MAXIMUM_PORT)
            step_name = port_definition.step_name
            container_port = port_definition.number
            port_packs.append((port_id, host_port, step_name))
            command_terms.extend(['-p', f'{host_port}:{container_port}'])
        command_terms.extend([
            '-v', f'{absolute_batch_folder}:/home/user/runs/next:Z'])
        process = _run_podman_command({
            'cwd': automation_folder,
            'capture_output': True,
        }, ['run'] + command_terms + ['-d', image_name])
        if process.returncode == 0:
            break
    container_id = process.stdout.decode().rstrip()
    return container_id, port_packs


def _get_image_name(automation_definition):
    automation_slug = automation_definition.slug
    automation_version = automation_definition.version
    return f'{automation_slug}:{automation_version}'


@contextmanager
def _proxy_podman_ports(
        automation_definition, batch_folder, custom_environment, port_packs):
    # TODO: Check if this works in jupyterlab extension
    origin_uri = custom_environment.get('CROSSCOMPUTE_ORIGIN_URI', '')
    relative_uris = []
    if PROXY_URI:
        def get_port_uri(target_uri, relative_uri):
            requests.post(PROXY_URI + relative_uri, json={
                'target': target_uri})
            relative_uris.append(relative_uri)
            return origin_uri + relative_uri
    else:
        def get_port_uri(target_uri, relative_uri):
            return target_uri
    automation_uri = AUTOMATION_ROUTE.format(
        automation_slug=automation_definition.slug)
    batch_uri = BATCH_ROUTE.format(batch_slug=batch_folder.name)
    absolute_batch_folder = automation_definition.folder / batch_folder
    port_uri_by_port_id = {}
    for port_id, host_port, step_name in port_packs:
        step_code = STEP_CODE_BY_NAME[step_name]
        variable_id = port_id
        relative_uri = PORT_ROUTE.format(
            uri=f'{automation_uri}{batch_uri}/{step_code}/{variable_id}')
        port_uri_by_port_id[port_id] = get_port_uri(
            f'http://localhost:{host_port}', relative_uri)
    update_variable_data(
        absolute_batch_folder / 'debug' / 'ports.dictionary',
        port_uri_by_port_id)
    try:
        yield
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        for relative_uri in relative_uris:
            requests.delete(PROXY_URI + relative_uri)


def _copy_datasets_into_podman(container_id, automation_definition):
    automation_folder = automation_definition.folder
    for dataset_definition in automation_definition.dataset_definitions:
        dataset_path = dataset_definition.path
        _make_podman_folder(container_id, dataset_path.parent)
        _run_podman_command({'cwd': automation_folder}, [
            'cp', dataset_path, f'{container_id}:{dataset_path}'])


def _set_podman_folder_owner(folder, user_id):
    _run_podman_command({}, [
        'unshare', 'chown', f'{user_id}:{user_id}', str(folder), '-R'])


def _make_podman_folder(container_id, folder):
    _run_podman_command({}, ['exec', container_id, 'mkdir', folder, '-p'])


def _run_podman_command(options, terms):
    command_terms = ['podman'] + terms
    L.debug(command_terms)
    return subprocess.run(command_terms, **options)


def _process_podman_return_code(return_code, absolute_batch_folder):
    if return_code in [126, 127]:
        x = 'denied permission' if return_code == 126 else 'not found'
        error = CrossComputeConfigurationError(
            'command %s in container; check script definitions' % x)
        error.code = Error.COMMAND_NOT_RUNNABLE
        raise error
    elif return_code != 0:
        error_text = (
            absolute_batch_folder / 'debug' / 'stderr.txt'
        ).read_text()
        error = CrossComputeExecutionError(error_text.rstrip())
        error.code = return_code
        raise error
    return return_code


CONTAINER_IGNORE_TEXT = '''\
**/.git
**/.gitignore
**/.gitmodules
**/.ipynb_checkpoints
**/batches
**/datasets
**/runs
**/tests
.containerfile
.containerignore'''
CONTAINER_FILE_NAME = '.containerfile'
CONTAINER_FILE_TEXT = Template('''\
FROM {{ parent_image_name }}
WORKDIR /home/user
RUN \
{% if root_package_commands %}
{{ ' && '.join(root_package_commands) }} && \
{% endif %}
if command -v useradd > /dev/null; then useradd user; \
else addgroup -S user && adduser -G user -S user; fi && \
chown user:user /home/user -R
USER user
{% if path_folders %}
ENV PATH="${PATH}:{{ ':'.join(path_folders) }}"
{% endif %}
{% if user_package_commands %}
RUN \
{{ ' && '.join(user_package_commands) }}
{% endif %}
{% if port_numbers %}
EXPOSE {{ ' '.join(port_numbers) }}
{% endif %}
COPY --chown=user:user . .
CMD ["sleep", "infinity"]''', trim_blocks=True)
CONTAINER_PIPE_TEXT = (
    ' 1>runs/next/debug/stdout.txt'
    ' 2>runs/next/debug/stderr.txt')
CONTAINER_SCRIPT_NAME = '.run.sh'
CONTAINER_ENV_NAME = '.run.env'
CONTAINER_STEP_FOLDER_BY_NAME = {
    _ + '_folder': 'runs/next/' + _ for _ in STEP_NAMES}
L = getLogger(__name__)

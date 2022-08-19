# TODO: Return unvalidated configuration when there is an exception
# TODO: Watch multiple folders if not all under parent folder
# TODO: Kill running containers at exit
import requests
import shlex
import subprocess
from contextlib import contextmanager
from collections import defaultdict
from concurrent.futures import (
    ProcessPoolExecutor, ThreadPoolExecutor, as_completed)
from datetime import datetime
from logging import getLogger
from multiprocessing import Manager, Queue
from os import environ, getenv, symlink
from os.path import relpath
from pathlib import Path
from time import sleep, time
from urllib.error import URLError
from urllib.request import urlretrieve as download_url

from invisibleroads_macros_disk import make_folder
from jinja2 import Template

from ..constants import (
    Error,
    AUTOMATION_PATH,
    AUTOMATION_ROUTE,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_CODE_BY_NAME,
    MODE_NAMES,
    PORT,
    PROXY_URI,
    RUN_ROUTE,
    TOKEN_LENGTH)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError,
    CrossComputeExecutionError)
from ..macros.iterable import group_by
from ..macros.security import DictionarySafe
from ..macros.web import find_open_port
from .configuration import (
    get_folder_plus_path,
    load_configuration)
from .interface import Automation
from .server import DiskServer
from .variable import (
    get_variable_data_by_id,
    get_variable_value_by_id,
    process_variable_data,
    save_variable_data,
    update_variable_data)


class DiskAutomation(Automation):

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        path_or_folder = Path(path_or_folder)
        if path_or_folder.is_dir():
            instance._initialize_from_folder(path_or_folder)
        else:
            instance._initialize_from_path(path_or_folder)
        with ThreadPoolExecutor() as executor:
            futures = []
            for automation_definition in instance.definitions:
                futures.extend(executor.submit(
                    _.get_command_string
                ) for _ in automation_definition.script_definitions)
            for future in as_completed(futures):
                future.result()
        return instance

    def run(self, user_environment, with_rebuild=True):
        for automation_definition in self.definitions:
            prepare_automation(automation_definition, with_rebuild)
        recurring_definitions = []
        for automation_definition in self.definitions:
            run_automation(
                automation_definition, user_environment, with_rebuild)
            if automation_definition.interval_timedelta:
                recurring_definitions.append(automation_definition)
        if not recurring_definitions:
            return
        while True:
            for automation_definition in recurring_definitions:
                last = automation_definition.interval_datetime
                delta = automation_definition.interval_timedelta
                if datetime.now() > last + delta:
                    run_automation(
                        automation_definition, user_environment,
                        with_rebuild=False)
            sleep(1)

    def serve(
            self, environment, host=HOST, port=PORT, with_refresh=False,
            with_restart=False, root_uri='', allowed_origins=None,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
        queue = Queue()
        with Manager() as manager:
            infos_by_timestamp = manager.dict()
            safe = DictionarySafe({}, manager.dict(), TOKEN_LENGTH)
            server = DiskServer(
                environment, safe, queue, _work, infos_by_timestamp, host,
                port, with_refresh, with_restart, root_uri, allowed_origins)
            configuration = self.configuration
            if not with_refresh and not with_restart:
                server.serve(configuration)
            else:
                server.watch(
                    configuration,
                    disk_poll_in_milliseconds,
                    disk_debounce_in_milliseconds,
                    self._reload)

    def _reload(self):
        path = self.path
        if path.exists():
            self._initialize_from_path(path)
        else:
            self._initialize_from_folder(self.folder)
        return self.configuration

    def _initialize_from_folder(self, folder):
        paths = list(folder.iterdir())
        default_automation_path = folder / AUTOMATION_PATH
        if default_automation_path in paths:
            paths.remove(default_automation_path)
            paths.insert(0, default_automation_path)
        for path in paths:
            if path.is_dir():
                continue
            try:
                self._initialize_from_path(path)
            except CrossComputeConfigurationFormatError:
                continue
            except (CrossComputeConfigurationError, CrossComputeDataError):
                raise
            except CrossComputeError:
                continue
            break
        else:
            raise CrossComputeConfigurationNotFoundError(
                'configuration not found')

    def _initialize_from_path(self, path):
        configuration = load_configuration(path)
        self.configuration = configuration
        self.path = path
        self.folder = configuration.folder
        self.definitions = configuration.automation_definitions


class AbstractEngine():

    def __init__(self, with_rebuild=True):
        self.with_rebuild = with_rebuild

    def run_batch(
            self, automation_definition, batch_definition, user_environment):
        reference_time = time()
        batch_folder, batch_environment = _prepare_batch(
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
        else:
            L.info('%s done', batch_identifier)
        return _process_batch(automation_definition, batch_definition, [
            'output', 'log', 'debug',
        ], {'debug': {
            'execution_time_in_seconds': time() - reference_time,
            'return_code': return_code,
        }})

    def prepare(self, automation_definition):
        pass


class UnsafeEngine(AbstractEngine):

    def run(self, automation_definition, batch_folder, custom_environment):
        mode_folder_by_name = _get_mode_folder_by_name(
            automation_definition.folder, batch_folder)
        script_environment = _prepare_script_environment(
            mode_folder_by_name, custom_environment, with_path=True)
        debug_folder = mode_folder_by_name['debug_folder']
        o_path = debug_folder / 'stdout.txt'
        e_path = debug_folder / 'stderr.txt'
        with open(o_path, 'wt') as o_file, open(e_path, 'w+t') as e_file:
            for script_definition in automation_definition.script_definitions:
                return_code = _run_script(
                    script_definition, mode_folder_by_name,
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
            _.get_command_string().format(**CONTAINER_MODE_FOLDER_BY_NAME)
            for _ in automation_definition.script_definitions]
        (automation_folder / CONTAINER_SCRIPT_NAME).write_text(
            '\n'.join([_ + CONTAINER_PIPE_TEXT for _ in command_texts]))
        if subprocess.run([
            'podman', 'build', '-t', image_name, '-f', CONTAINER_FILE_NAME,
        ], cwd=automation_folder).returncode != 0:
            raise CrossComputeExecutionError(f'could not build "{image_name}"')

    def run(self, automation_definition, batch_folder, custom_environment):
        container_id, port_packs = _run_podman_image(
            automation_definition, batch_folder, custom_environment)
        with _proxy_podman_ports(
                automation_definition, batch_folder, custom_environment,
                port_packs):
            return_code = _run_podman_script(
                automation_definition, batch_folder, container_id)
        if return_code in [126, 127]:
            error_text = (
                'permission denied' if return_code == 126 else 'not found')
            error = CrossComputeConfigurationError(
                f'command {error_text} in container; please check script '
                'definitions')
            error.code = Error.COMMAND_NOT_RUNNABLE
            raise error
        elif return_code > 0:
            error_text = (batch_folder / 'debug' / 'stderr.txt').read_text()
            error = CrossComputeExecutionError(error_text.rstrip())
            error.code = return_code
            raise error
        return return_code


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
        target_path = (automation_folder / dataset_definition.path).resolve()
        target_folder = make_folder(target_path.parent)
        reference_configuration = dataset_definition.reference
        reference_path = get_folder_plus_path(reference_configuration)
        if reference_path:
            source_path = (automation_folder / reference_path).resolve()
            if target_path.is_symlink():
                if target_path == source_path:
                    continue
                target_path.unlink()
            elif target_path.exists():
                continue
            symlink(relpath(source_path, target_folder), target_path)
        elif 'url' in reference_configuration:
            reference_url = reference_configuration['url']
            try:
                download_url(reference_url, target_path)
            except URLError:
                L.error(f'could not download dataset from {reference_url}')


def prepare_automation(automation_definition, with_rebuild=True):
    engine = get_script_engine(automation_definition.engine_name, with_rebuild)
    engine.prepare(automation_definition)


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
    automation_definition.interval_datetime = datetime.now()
    return ds


def _run_automation_single(
        automation_definition, run_batch, user_environment):
    ds = []
    for batch_definition in automation_definition.batch_definitions:
        ds.append(run_batch(
            automation_definition, batch_definition, user_environment))
    return ds


def _run_automation_multiple(
        automation_definition, run_batch, user_environment, concurrency_name):
    ds = []
    if concurrency_name == 'process':
        BatchExecutor = ProcessPoolExecutor
    else:
        BatchExecutor = ThreadPoolExecutor
    with BatchExecutor() as executor:
        futures = []
        for batch_definition in automation_definition.batch_definitions:
            futures.append(executor.submit(
                run_batch, automation_definition, batch_definition,
                user_environment))
        for future in as_completed(futures):
            ds.append(future.result())
    return ds


def _run_script(
        script_definition, mode_folder_by_name, script_environment,
        stdout_file, stderr_file):
    command_string = script_definition.get_command_string()
    if not command_string:
        return
    command_text = command_string.format(**mode_folder_by_name)
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


def _has_podman_image(image_name):
    return _run_podman_command({}, [
        'image', 'exists', image_name]).returncode == 0


def _run_podman_image(automation_definition, batch_folder, custom_environment):
    automation_folder = automation_definition.folder
    container_env_path = automation_folder / CONTAINER_ENV_NAME
    script_environment = _prepare_script_environment(
        CONTAINER_MODE_FOLDER_BY_NAME, custom_environment, with_path=False)
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
            host_port = find_open_port()
            mode_name = port_definition.mode_name
            container_port = port_definition.number
            port_packs.append((port_id, host_port, mode_name))
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


@contextmanager
def _proxy_podman_ports(
        automation_definition, batch_folder, custom_environment, port_packs):
    origin_uri = custom_environment.get('CROSSCOMPUTE_ORIGIN_URI', '')
    relative_uris = []
    if PROXY_URI:
        def get_session_uri(host_port, relative_uri):
            requests.post(PROXY_URI + relative_uri, json={
                'target': f'http://localhost:{host_port}'})
            relative_uris.append(relative_uri)
            return origin_uri + relative_uri
    else:
        def get_session_uri(host_port, relative_uri):
            return f'http://localhost:{host_port}'
    automation_uri = AUTOMATION_ROUTE.format(
        automation_slug=automation_definition.slug)
    run_uri = RUN_ROUTE.format(run_slug=batch_folder.name)
    absolute_batch_folder = automation_definition.folder / batch_folder
    for port_id, host_port, mode_name in port_packs:
        port_path = absolute_batch_folder / 'debug' / 'ports.dictionary'
        mode_code = MODE_CODE_BY_NAME[mode_name]
        variable_id = port_id
        relative_uri = (
            f'/sessions{automation_uri}{run_uri}/{mode_code}'
            f'/{variable_id}')
        session_uri = get_session_uri(host_port, relative_uri)
        update_variable_data(port_path, {port_id: session_uri})
    yield
    for relative_uri in relative_uris:
        requests.delete(PROXY_URI + relative_uri)


def _run_podman_script(automation_definition, batch_folder, container_id):
    automation_folder = automation_definition.folder
    absolute_batch_folder = automation_folder / batch_folder

    for dataset_definition in automation_definition.dataset_definitions:
        dataset_path = dataset_definition.path
        _run_podman_command({}, [
            'exec', container_id, 'mkdir', dataset_path.parent, '-p'])
        _run_podman_command({'cwd': automation_folder}, [
            'cp', dataset_path, f'{container_id}:{dataset_path}'])

    _run_podman_command({}, [
        'unshare', 'chown', '1000:1000', str(absolute_batch_folder), '-R'])
    process = _run_podman_command({'cwd': automation_folder}, [
        'exec', '--env-file', CONTAINER_ENV_NAME, container_id,
        'bash', CONTAINER_SCRIPT_NAME])
    _run_podman_command({}, [
        'unshare', 'chown', '0:0', str(absolute_batch_folder), '-R'])

    _run_podman_command({}, ['kill', container_id])
    return process.returncode


def _run_podman_command(options, terms):
    command_terms = ['podman'] + terms
    L.debug(command_terms)
    return subprocess.run(command_terms, **options)


def _work(automation_queue):
    try:
        while automation_pack := automation_queue.get():
            automation_definition = automation_pack[0]
            engine = get_script_engine(
                automation_definition.engine_name, with_rebuild=False)
            update_datasets(automation_definition)
            try:
                engine.run_batch(*automation_pack)
            except CrossComputeError as e:
                e.automation_definition = automation_definition
                L.error(e)
    except KeyboardInterrupt:
        pass


def _prepare_batch(automation_definition, batch_definition):
    variable_definitions = automation_definition.get_variable_definitions(
        'input')
    variable_definitions_by_path = group_by(variable_definitions, 'path')
    data_by_id = batch_definition.data_by_id
    batch_folder = batch_definition.folder
    batch_environment = _prepare_batch_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    mode_folder_by_name = _make_mode_folder_by_name(
        automation_definition.folder, batch_folder)
    if not data_by_id:
        return batch_folder, batch_environment
    input_folder = mode_folder_by_name['input_folder']
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = input_folder / path
        save_variable_data(input_path, data_by_id, variable_definitions)
    return batch_folder, batch_environment


def _make_mode_folder_by_name(automation_folder, batch_folder):
    mode_folder_by_name = _get_mode_folder_by_name(
        automation_folder, batch_folder)
    for folder in mode_folder_by_name.values():
        folder.mkdir(parents=True, exist_ok=True)
    return mode_folder_by_name


def _get_mode_folder_by_name(automation_folder, batch_folder):
    return {
        _ + '_folder': automation_folder / batch_folder / _
        for _ in MODE_NAMES}


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


def _prepare_script_environment(
        mode_folder_by_name, custom_environment, with_path=False):
    script_environment = {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in mode_folder_by_name.items()
    } | custom_environment
    if with_path:
        script_environment['PATH'] = getenv('PATH', '')
    return script_environment


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


def _process_batch(
        automation_definition, batch_definition, mode_names,
        extra_data_by_id_by_mode_name):
    variable_data_by_id_by_mode_name = {}
    automation_folder = automation_definition.folder
    batch_folder = batch_definition.folder
    for mode_name in mode_names:
        variable_data_by_id_by_mode_name[mode_name] = variable_data_by_id = {}
        extra_data_by_id = extra_data_by_id_by_mode_name.get(mode_name, {})
        mode_folder = automation_folder / batch_folder / mode_name
        variable_definitions = automation_definition.get_variable_definitions(
            mode_name)
        for variable_definition in variable_definitions:
            variable_id = variable_definition.id
            variable_path = variable_definition.path
            if variable_id in extra_data_by_id:
                continue
            path = mode_folder / variable_path
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
                mode_folder / 'variables.dictionary', extra_data_by_id)
            variable_data_by_id.update(extra_data_by_id)
    return variable_data_by_id_by_mode_name


def _get_image_name(automation_definition):
    automation_slug = automation_definition.slug
    automation_version = automation_definition.version
    return f'{automation_slug}:{automation_version}'


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
RUN \
{% if user_package_commands %}
{{ ' && '.join(user_package_commands) }}
{% endif %}
{% if port_numbers %}
EXPOSE {{ ' '.join(port_numbers) }}
{% endif %}
COPY --chown=user:user . .
CMD ["sleep", "infinity"]''', trim_blocks=True)
CONTAINER_PIPE_TEXT = (
    ' 1>>runs/next/debug/stdout.txt'
    ' 2>>runs/next/debug/stderr.txt')
CONTAINER_SCRIPT_NAME = '.run.sh'
CONTAINER_ENV_NAME = '.run.env'
CONTAINER_MODE_FOLDER_BY_NAME = {
    _ + '_folder': 'runs/next/' + _ for _ in MODE_NAMES}


L = getLogger(__name__)

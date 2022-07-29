# TODO: Watch multiple folders if not all under parent folder
import shlex
import shutil
import subprocess
from collections import defaultdict
from concurrent.futures import (
    ProcessPoolExecutor, ThreadPoolExecutor, as_completed)
from datetime import datetime
from functools import partial
from jinja2 import Template
from logging import getLogger
from multiprocessing import Manager
from os import environ, getenv, symlink
from os.path import relpath
from pathlib import Path
from time import sleep, time
from urllib.error import URLError
from urllib.request import urlretrieve as download_url

from invisibleroads_macros_disk import make_folder

from ..constants import (
    Error,
    Status,
    AUTOMATION_PATH,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_NAMES,
    PORT,
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

    def run(self, engine_name=None, with_rebuild=True):
        engine = get_script_engine(engine_name, with_rebuild)
        engine.run_configuration(self)

    def serve(
            self, queue, engine, host=HOST, port=PORT,
            with_refresh=False, with_restart=False, root_uri='',
            allowed_origins=None,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
        work = partial(_work, run_batch=engine.run_batch)
        with Manager() as manager:
            infos_by_timestamp = manager.dict()
            safe = DictionarySafe({}, manager.dict(), TOKEN_LENGTH)
            server = DiskServer(
                safe, queue, work, infos_by_timestamp, host, port,
                with_refresh, with_restart, root_uri, allowed_origins)
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

    def run_configuration(self, configuration):
        for automation_definition in configuration.definitions:
            self.prepare(automation_definition)
        recurring_definitions = []
        for automation_definition in configuration.definitions:
            run_automation(
                automation_definition, self.run_batch, self.with_rebuild)
            if automation_definition.interval_timedelta:
                recurring_definitions.append(automation_definition)
        if not recurring_definitions:
            return
        while True:
            for automation_definition in recurring_definitions:
                last = automation_definition.interval_datetime
                delta = automation_definition.interval_timedelta
                if datetime.now() > last + delta:
                    run_automation(automation_definition, self.run_batch)
            sleep(1)

    def run_batch(self, automation_definition, batch_definition):
        reference_time = time()
        batch_folder, custom_environment = _prepare_batch(
            automation_definition, batch_definition)
        if not automation_definition.script_definitions:
            return
        batch_identifier = ' '.join([
            automation_definition.name,
            automation_definition.version,
            str(batch_folder)])
        L.info('%s running', batch_identifier)
        try:
            return_code = self.run(
                automation_definition, batch_folder, custom_environment)
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
        ], {
            'debug': {
                'execution_time_in_seconds': time() - reference_time,
                'return_code': return_code,
            },
        })

    def prepare(self, automation_definition):
        pass


class UnsafeEngine(AbstractEngine):

    def run(
            self, automation_definition, batch_folder, custom_environment):
        automation_folder = automation_definition.folder
        mode_folder_by_name = {_ + '_folder': make_folder(
            automation_folder / batch_folder / _
        ) for _ in MODE_NAMES}
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
        automation_folder = automation_definition.folder
        container_file_path = automation_folder / CONTAINER_FILE_NAME
        if not self.with_rebuild and container_file_path.exists():
            return
        (automation_folder / CONTAINER_FILE_NAME).write_text(
            _prepare_container_file_text(automation_definition))
        (automation_folder / '.containerignore').write_text(
            CONTAINER_IGNORE_TEXT)
        command_texts = [
            _.get_command_string().format(**CONTAINER_MODE_FOLDER_BY_NAME)
            for _ in automation_definition.script_definitions]
        (automation_folder / CONTAINER_SCRIPT_NAME).write_text(
            '\n'.join([_ + CONTAINER_PIPE_TEXT for _ in command_texts]))
        image_name = _get_image_name(automation_definition)
        if subprocess.run([
            'podman', 'build', '-t', image_name, '-f', CONTAINER_FILE_NAME,
        ], cwd=automation_folder).returncode != 0:
            raise CrossComputeExecutionError(f'could not build "{image_name}"')

    def run(
            self, automation_definition, batch_folder, custom_environment):
        image_name = _get_image_name(automation_definition)
        if subprocess.run([
            'podman', 'image', 'exists', image_name,
        ]).returncode != 0:
            self.prepare(automation_definition)
        automation_folder = automation_definition.folder
        script_environment = _prepare_script_environment(
            CONTAINER_MODE_FOLDER_BY_NAME, custom_environment, with_path=False)
        (automation_folder / CONTAINER_ENV_NAME).write_text('\n'.join(
            f'{k}={v}' for k, v in script_environment.items()))
        return_code = _run_podman(
            automation_folder, batch_folder, image_name,
            automation_definition.dataset_definitions)
        return return_code


def get_script_engine(engine_name=None, with_rebuild=True):
    if not engine_name:
        engine_name = 'podman' if shutil.which('podman') else 'unsafe'
    if engine_name == 'unsafe':
        L.warning(
            'using engine=unsafe; use engine=podman for untrusted code')
    try:
        ScriptEngine = {
            'unsafe': UnsafeEngine,
            'podman': PodmanEngine,
        }[engine_name]
    except KeyError:
        raise CrossComputeExecutionError(f'unsupported engine "{engine_name}"')
    return ScriptEngine(
        with_rebuild=with_rebuild)


def update_datasets(automation_definition):
    # TODO: Download from URL
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


def run_automation(automation_definition, run_batch, with_rebuild=True):
    ds = []
    concurrency_name = automation_definition.batch_concurrency_name
    update_datasets(automation_definition)
    try:
        if concurrency_name == 'single':
            ds.extend(_run_automation_single(
                automation_definition, run_batch, with_rebuild))
        else:
            ds.extend(_run_automation_multiple(
                automation_definition, run_batch, with_rebuild,
                concurrency_name))
    except CrossComputeError as e:
        e.automation_definition = automation_definition
        L.error(e)
    automation_definition.interval_datetime = datetime.now()
    return ds


def _run_automation_single(automation_definition, run_batch, with_rebuild):
    ds = []
    for batch_definition in automation_definition.batch_definitions:
        batch_status = batch_definition.get_status()
        if not with_rebuild and batch_status != Status.NEW:
            continue
        ds.append(run_batch(automation_definition, batch_definition))
    return ds


def _run_automation_multiple(
        automation_definition, run_batch, with_rebuild, concurrency_name):
    ds = []
    if concurrency_name == 'process':
        BatchExecutor = ProcessPoolExecutor
    else:
        BatchExecutor = ThreadPoolExecutor
    with BatchExecutor() as executor:
        futures = []
        for batch_definition in automation_definition.batch_definitions:
            batch_status = batch_definition.get_status()
            if not with_rebuild and batch_status != Status.NEW:
                continue
            futures.append(executor.submit(
                run_batch, automation_definition, batch_definition))
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


def _run_podman(
        automation_folder, batch_folder, image_name, dataset_definitions):
    container_id = _run_podman_command({'capture_output': True}, [
        'run', '-d', image_name]).stdout.decode().rstrip()
    for dataset_definition in dataset_definitions:
        dataset_path = dataset_definition.path
        _run_podman_command({}, [
            'exec', container_id, 'mkdir', dataset_path.parent, '-p'])
        _run_podman_command({'cwd': automation_folder}, [
            'cp', dataset_path, f'{container_id}:{dataset_path}'])
    container_batch_folder = f'{container_id}:runs/next/'
    _run_podman_command({'cwd': automation_folder}, [
        'cp', batch_folder / 'input', container_batch_folder])
    return_code = _run_podman_command({'cwd': automation_folder}, [
        'exec', '--env-file', CONTAINER_ENV_NAME, container_id, 'bash',
        CONTAINER_SCRIPT_NAME,
    ]).returncode
    _run_podman_command({'cwd': automation_folder}, [
        'cp', container_batch_folder + '.', batch_folder])
    _run_podman_command({}, ['kill', container_id])
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


def _run_podman_command(options, terms):
    return subprocess.run(['podman'] + terms, **options)


def _work(automation_queue, run_batch):
    try:
        while automation_pack := automation_queue.get():
            automation_definition, batch_definition = automation_pack
            update_datasets(automation_definition)
            try:
                run_batch(automation_definition, batch_definition)
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
    custom_environment = _prepare_custom_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    if not data_by_id:
        return batch_folder, custom_environment
    automation_folder = automation_definition.folder
    input_folder = make_folder(automation_folder / batch_folder / 'input')
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = input_folder / path
        save_variable_data(input_path, data_by_id, variable_definitions)
    return batch_folder, custom_environment


def _prepare_container_file_text(automation_definition):
    package_ids_by_manager_name = defaultdict(set)
    for package_definition in automation_definition.package_definitions:
        package_id = package_definition.id
        manager_name = package_definition.manager_name
        package_ids_by_manager_name[manager_name].add(package_id)
    root_package_commands = []
    user_package_commands = []
    if 'apt' in package_ids_by_manager_name:
        package_ids_string = ' '.join(package_ids_by_manager_name['apt'])
        root_package_commands.append(
            f'apt update && apt -y install {package_ids_string} && apt clean')
    if 'dnf' in package_ids_by_manager_name:
        package_ids_string = ' '.join(package_ids_by_manager_name['dnf'])
        root_package_commands.append(
            f'dnf -y install {package_ids_string} && dnf clean all')
    if 'npm' in package_ids_by_manager_name:
        package_ids_string = ' '.join(package_ids_by_manager_name['npm'])
        user_package_commands.append(
            f'npm install {package_ids_string} && npm cache clean --force')
    if 'pip' in package_ids_by_manager_name:
        package_ids_string = ' '.join(package_ids_by_manager_name['pip'])
        user_package_commands.append(
            f'pip install {package_ids_string} --user && pip cache purge')
    return CONTAINER_FILE_TEXT.render(
        root_package_commands=root_package_commands,
        user_package_commands=user_package_commands,
        parent_image_name=automation_definition.parent_image_name)


def _prepare_script_environment(
        mode_folder_by_name, custom_environment, with_path=False):
    script_environment = {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in mode_folder_by_name.items()
    } | custom_environment
    if with_path:
        script_environment['PATH'] = getenv('PATH', '')
    L.debug('environment = %s', script_environment)
    return script_environment


def _prepare_custom_environment(
        automation_definition, variable_definitions, data_by_id):
    custom_environment = {}
    for variable_id in automation_definition.environment_variable_ids:
        custom_environment[variable_id] = environ[variable_id]
    for variable_id in (_.id for _ in variable_definitions):
        if variable_id in data_by_id:
            continue
        try:
            custom_environment[variable_id] = environ[variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'{variable_id} is missing in the environment')
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id, with_exceptions=False)
    variable_value_by_id = get_variable_value_by_id(variable_data_by_id)
    return custom_environment | variable_value_by_id


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
RUN \
{% if user_package_commands %}
{{ ' && '.join(user_package_commands) }} && \
{% endif %}
mkdir runs/next/input runs/next/log runs/next/debug runs/next/output -p
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

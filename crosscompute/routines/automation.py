# TODO: Watch multiple folders if not all under parent folder
import shlex
import subprocess
from invisibleroads_macros_disk import make_folder
from logging import getLogger
from multiprocessing import Queue, Manager
from os import environ, getenv
from pathlib import Path
from time import time

from ..constants import (
    Error,
    AUTOMATION_PATH,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_NAMES,
    PORT)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError,
    CrossComputeExecutionError)
from ..macros.iterable import group_by
from .configuration import (
    load_configuration)
from .interface import Automation
from .server import DiskServer
from .variable import (
    get_variable_data_by_id,
    get_variable_value_by_id,
    load_variable_data,
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
        return instance

    def run(self):
        for automation_definition in self.definitions:
            batch_definitions = automation_definition.batch_definitions
            try:
                automation_definition.update_datasets()
                for batch_definition in batch_definitions:
                    _run_automation(
                        automation_definition, batch_definition,
                        process_data=load_variable_data)
            except CrossComputeError as e:
                e.automation_definition = automation_definition
                L.error(e)

    def serve(
            self,
            host=HOST,
            port=PORT,
            is_static=False,
            is_production=False,
            base_uri='',
            allowed_origins=None,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS,
            automation_queue=None):
        if automation_queue is None:
            automation_queue = Queue()
        with Manager() as manager:
            server_options = {
                'host': host,
                'port': port,
                'is_static': is_static,
                'is_production': is_production,
                'base_uri': base_uri,
                'allowed_origins': allowed_origins,
                'infos_by_timestamp': manager.dict(),
            }
            server = DiskServer(work, automation_queue, server_options)
            configuration = self.configuration
            if is_static and is_production:
                server.run(configuration)
                return
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


def work(automation_queue):
    try:
        while automation_pack := automation_queue.get():
            automation_definition, batch_definition = automation_pack
            try:
                automation_definition.update_datasets()
                _run_automation(
                    automation_definition, batch_definition,
                    process_data=load_variable_data)
            except CrossComputeError as e:
                e.automation_definition = automation_definition
                L.error(e)
    except KeyboardInterrupt:
        pass


def _run_automation(
        automation_definition, batch_definition, process_data):
    d = automation_definition
    script_definitions = d.script_definitions
    if not script_definitions:
        return
    reference_time = time()
    batch_folder, custom_environment = _prepare_batch(d, batch_definition)
    batch_identifier = ' '.join([d.name, d.version, str(batch_folder)])
    L.info('%s running', batch_identifier)
    mode_folder_by_name = {_ + '_folder': make_folder(
        d.folder / batch_folder / _) for _ in MODE_NAMES}
    script_environment = _prepare_script_environment(
        mode_folder_by_name, custom_environment)
    debug_folder = mode_folder_by_name['debug_folder']
    o_path = debug_folder / 'stdout.txt'
    e_path = debug_folder / 'stderr.txt'
    try:
        with open(o_path, 'wt') as o_file, open(e_path, 'w+t') as e_file:
            for script_definition in script_definitions:
                return_code = _run_script(
                    script_definition, mode_folder_by_name,
                    script_environment, o_file, e_file)
    except CrossComputeExecutionError as e:
        e.automation_definition = d
        L.error(e)
        return_code = e.return_code
        L.info('%s failed', batch_identifier)
    else:
        L.info('%s done', batch_identifier)
    return _process_batch(d, batch_definition, [
        'output', 'log', 'debug',
    ], {'debug': {
        'execution_time_in_seconds': time() - reference_time,
        'return_code': return_code}}, process_data)


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
        e = CrossComputeExecutionError(
            f'could not run {shlex.quote(command_string)} in {command_folder}')
        e.return_code = Error.COMMAND_NOT_FOUND
        raise e
    except subprocess.CalledProcessError as e:
        e_file.seek(0)
        error_text = e_file.read().rstrip()
        error = CrossComputeExecutionError(error_text)
        error.return_code = e.returncode
        raise error
    return process.returncode


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


def _prepare_script_environment(mode_folder_by_name, custom_environment):
    script_environment = {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in mode_folder_by_name.items()
    } | {'PATH': getenv('PATH', '')} | custom_environment
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
        extra_data_by_id_by_mode_name, process_data):
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
                variable_data = process_data(path, variable_id)
            except CrossComputeDataError as e:
                e.automation_definitions = automation_definition
                L.error(e)
                continue
            variable_data_by_id[variable_id] = variable_data
        if extra_data_by_id:
            update_variable_data(
                mode_folder / 'variables.dictionary', extra_data_by_id)
            variable_data_by_id.update(extra_data_by_id)
    return variable_data_by_id_by_mode_name


L = getLogger(__name__)

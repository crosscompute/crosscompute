import logging
import subprocess
from invisibleroads_macros_disk import make_folder
from invisibleroads_macros_log import format_path
from logging import getLogger
from multiprocessing import Process, Queue, Value
from os import environ, getenv, listdir
from os.path import isdir, join
from time import time
from waitress import serve

from ..constants import (
    AUTOMATION_PATH,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_NAMES,
    PORT)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from ..macros.iterable import group_by
from .configuration import (
    get_automation_definitions,
    get_raw_variable_definitions,
    load_configuration)
from .variable import (
    format_text,
    get_variable_data_by_id,
    save_variable_data)


class Automation():

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        if isdir(path_or_folder):
            instance.initialize_from_folder(path_or_folder)
        else:
            instance.initialize_from_path(path_or_folder)
        return instance

    def initialize_from_folder(self, configuration_folder):
        paths = listdir(configuration_folder)
        if AUTOMATION_PATH in paths:
            paths.remove(AUTOMATION_PATH)
            paths.insert(0, AUTOMATION_PATH)
        for path in paths:
            if isdir(path):
                continue
            try:
                self.initialize_from_path(path)
            except CrossComputeConfigurationError:
                raise
            except CrossComputeError:
                continue
            break
        else:
            raise CrossComputeError('could not find configuration')

    def initialize_from_path(self, configuration_path):
        configuration = load_configuration(configuration_path)
        automation_folder = configuration['folder']
        automation_definitions = get_automation_definitions(
            configuration)

        self.configuration_path = configuration_path
        self.configuration = configuration
        self.automation_folder = automation_folder
        self.automation_definitions = automation_definitions
        self.timestamp_object = Value('d', time())

        L.debug('configuration_path = %s', configuration_path)
        L.debug('automation_folder = %s', automation_folder)

    def serve(
            self,
            host=HOST,
            port=PORT,
            is_static=False,
            is_production=False,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS,
            base_uri='',
            automation_queue=None):
        if automation_queue is None:
            automation_queue = Queue()
        if getLogger().level > logging.DEBUG:
            getLogger('waitress').setLevel(logging.ERROR)
            getLogger('watchgod.watcher').setLevel(logging.ERROR)

        def run_server():
            L.info('starting worker')
            worker_process = Process(target=self.work, args=(
                automation_queue,))
            worker_process.start()
            L.info('serving at http://%s:%s%s', host, port, base_uri)
            app = self.get_app(automation_queue, is_static, base_uri)
            try:
                serve(app, host=host, port=port, url_prefix=base_uri)
            except OSError as e:
                L.error(e)

        if is_static and is_production:
            run_server()
            return

        self.watch(
            run_server, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds)

    def work(self, automation_queue):
        try:
            while automation_pack := automation_queue.get():
                run_automation(*automation_pack)
        except KeyboardInterrupt:
            pass


def run_automation(automation_definition, batch_definition):
    automation_folder = automation_definition['folder']
    batch_folder, custom_environment = prepare_batch(
        automation_definition, batch_definition)
    L.info(
        '%s %s running %s in %s',
        automation_definition['name'],
        automation_definition['version'],
        batch_definition['name'],
        format_path(join(automation_folder, batch_folder)))
    script_definition = automation_definition.get('script', {})
    command_string = script_definition.get('command')
    script_folder = script_definition.get('folder', '.')
    mode_folder_by_name = {_ + '_folder': make_folder(join(
        automation_folder, batch_folder, _)) for _ in MODE_NAMES}
    debug_folder = mode_folder_by_name['debug']
    script_environment = {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in mode_folder_by_name.items()
    } | {'PATH': getenv('PATH', '')} | custom_environment
    L.debug('environment = %s', script_environment)
    with open(join(
        debug_folder, 'stdout.txt',
    ), 'wt') as stdout_file, open(join(
        debug_folder, 'stderr.txt',
    ), 'wt') as stderr_file:
        subprocess.run(
            format_text(command_string, mode_folder_by_name),
            shell=True,  # Expand $HOME and ~
            cwd=join(automation_folder, script_folder),
            env=script_environment,
            stdout=stdout_file,
            stderr=stderr_file)


def prepare_batch(automation_definition, batch_definition):
    variable_definitions = get_raw_variable_definitions(
        automation_definition, 'input')
    batch_folder = batch_definition['folder']
    variable_definitions_by_path = group_by(variable_definitions, 'path')
    data_by_id = batch_definition.get('data_by_id', {})
    custom_environment = prepare_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    if not data_by_id:
        return batch_folder, custom_environment
    automation_folder = automation_definition['folder']
    input_folder = make_folder(join(automation_folder, batch_folder, 'input'))
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = join(input_folder, path)
        save_variable_data(input_path, variable_definitions, data_by_id)
    return batch_folder, custom_environment


def prepare_environment(
        automation_definition, variable_definitions, data_by_id):
    custom_environment = {}
    data_by_id = data_by_id.copy()
    try:
        environment_variable_definitions = automation_definition.get(
            'environment', {}).get('variables', [])
        for variable_id in (_['id'] for _ in environment_variable_definitions):
            custom_environment[variable_id] = environ[variable_id]
        for variable_id in (_['id'] for _ in variable_definitions):
            if variable_id in data_by_id:
                continue
            data_by_id[variable_id] = environ[variable_id]
    except KeyError:
        raise CrossComputeConfigurationError(
            f'{variable_id} is missing in the environment')
    return custom_environment | get_variable_data_by_id(
        variable_definitions, data_by_id)


L = getLogger(__name__)

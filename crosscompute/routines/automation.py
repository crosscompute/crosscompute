# TODO: Watch multiple folders if not all under parent folder
import logging
import subprocess
from invisibleroads_macros_disk import has_changed, make_folder
from invisibleroads_macros_log import format_path
from logging import getLogger
from multiprocessing import Process, Queue, Value
from os import environ, getenv, listdir
from os.path import exists, isdir, join, splitext
from time import time
from waitress import serve
from watchgod import watch

from ..constants import (
    AUTOMATION_PATH,
    CONFIGURATION_EXTENSIONS,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_NAMES,
    PORT,
    STYLE_EXTENSIONS)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from ..macros.iterable import group_by
from .configuration import (
    get_automation_definitions,
    get_display_configuration,
    get_raw_variable_definitions,
    load_configuration)
from .disk import get_hash_by_path
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

    def reload(self):
        configuration_path = self.configuration_path
        if exists(configuration_path):
            self.initialize_from_path(configuration_path)
        else:
            self.initialize_from_folder(self.automation_folder)

    def reload_display_configuration(self):
        pass

    def initialize_from_folder(self, configuration_folder):
        paths = listdir(configuration_folder)
        if AUTOMATION_PATH in paths:
            paths.remove(AUTOMATION_PATH)
            paths.insert(0, AUTOMATION_PATH)
        for relative_path in paths:
            absolute_path = join(configuration_folder, relative_path)
            if isdir(absolute_path):
                continue
            try:
                self.initialize_from_path(absolute_path)
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
        self.watched_paths = set([configuration_path])

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
            worker_process.daemon = True
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

    def run(self):
        for automation_definition in self.automation_definitions:
            for batch_definition in automation_definition.get('batches', []):
                run_automation(automation_definition, batch_definition)

    def work(self, automation_queue):
        try:
            while automation_pack := automation_queue.get():
                run_automation(*automation_pack)
        except KeyboardInterrupt:
            pass

    def watch(
            self, run_server, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds):
        # server_process = StoppableProcess(target=run_server)
        # server_process.start()
        # TODO: !!! think about watched_paths and if this complication is needed
        hash_by_path = get_hash_by_path(self.watched_paths)
        for changes in watch(
                self.automation_folder, min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            for changed_type, changed_path in changes:
                L.debug('%s %s', changed_type, changed_path)
                if not has_changed(changed_path, hash_by_path):
                    continue
                changed_extension = splitext(changed_path)[1]
                if changed_extension in CONFIGURATION_EXTENSIONS:
                    try:
                        self.reload()
                    except CrossComputeError as e:
                        L.error(e)
                        continue
                    hash_by_path = get_hash_by_path(self.get_paths())
                    # server_process.stop()
                    # server_process = StoppableProcess(target=run_server)
                    # server_process.start()
                elif changed_extension in STYLE_EXTENSIONS:
                    for d in self.automation_definitions:
                        d['display'] = get_display_configuration(d)
                    self.timestamp_object.value = time()
                # elif changed_extension in TEMPLATE_EXTENSIONS:
                    # self.timestamp_object.value = time()
                else:
                    # TODO: Send partial updates
                    self.timestamp_object.value = time()

    def get_paths(self):
        paths = set([self.configuration_path])
        '''
        for automation_definition in self.automation_definitions:
            automation_folder = automation_definition['folder']
            configuration = load_configuration(automation_definition['path'])
            for mode_name in MODE_NAMES:
                mode_configuration = automation_definition.get(mode_name, {})
                template_definitions = mode_configuration.get('templates', [])
                for template_definition in template_definitions:
                    if 'path' not in template_definition:
                        continue
                    paths.add(join(
                        automation_folder, template_definition['path']))

            # TODO: Watch only on view
            for batch_definition in automation_definition.get('batches', []):
                paths.update(get_paths_from_folder(join(
                    automation_folder, batch_definition['folder'])))

            for batch_definition in configuration.get('batches', []):
                batch_configuration = batch_definition.get('configuration', {})
                if 'path' not in batch_configuration:
                    continue
                paths.add(join(
                    automation_folder, batch_configuration['path']))
            display_configuration = automation_definition.get('display', {})
            for style_definition in display_configuration.get('styles', []):
                if 'path' not in style_definition:
                    continue
                paths.add(join(automation_folder, style_definition['path']))

            paths.add(automation_definition['path'])
        '''
        return paths


def run_automation(automation_definition, batch_definition):
    script_definition = automation_definition.get('script', {})
    command_string = script_definition.get('command')
    if not command_string:
        return
    automation_folder = automation_definition['folder']
    batch_folder, custom_environment = prepare_batch(
        automation_definition, batch_definition)
    L.info(
        '%s %s running %s in %s',
        automation_definition['name'],
        automation_definition['version'],
        batch_definition['name'],
        format_path(join(automation_folder, batch_folder)))
    script_folder = script_definition.get('folder', '.')
    mode_folder_by_name = {_ + '_folder': make_folder(join(
        automation_folder, batch_folder, _)) for _ in MODE_NAMES}
    script_environment = {
        'CROSSCOMPUTE_' + k.upper(): v for k, v in mode_folder_by_name.items()
    } | {'PATH': getenv('PATH', '')} | custom_environment
    L.debug('environment = %s', script_environment)
    debug_folder = mode_folder_by_name['debug_folder']
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

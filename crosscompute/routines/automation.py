# TODO: Trigger refresh on variable configuration update
# TODO: Watch multiple folders if not all under parent folder
# TODO: Consider whether to send partial updates for variables
# TODO: Precompile notebook scripts
import logging
import subprocess
from logging import getLogger
from multiprocessing import Queue, Value
from os import environ, getenv, listdir
from os.path import exists, isdir, join, realpath
from time import time

from invisibleroads_macros_disk import is_path_in_folder, make_folder
from invisibleroads_macros_log import format_path
from pyramid.config import Configurator
from pyramid.events import NewResponse
from waitress import serve
from watchgod import watch

from ..constants import (
    Error,
    AUTOMATION_PATH,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    MODE_NAMES,
    PORT,
    STREAMS_ROUTE)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError)
from ..macros.iterable import group_by
from ..macros.process import LoggableProcess, StoppableProcess
from ..routes.automation import AutomationRoutes
from ..routes.stream import StreamRoutes
from .configuration import (
    get_automation_definitions,
    get_display_configuration,
    get_variable_definitions,
    load_configuration)
from .variable import (
    get_variable_data_by_id,
    get_variable_value_by_id,
    load_variable_data,
    save_variable_data,
    update_variable_data)


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
        path = self.path
        if exists(path):
            self.initialize_from_path(path)
        else:
            self.initialize_from_folder(self.folder)

    def initialize_from_folder(self, folder):
        paths = listdir(folder)
        if AUTOMATION_PATH in paths:
            paths.remove(AUTOMATION_PATH)
            paths.insert(0, AUTOMATION_PATH)
        for relative_path in paths:
            absolute_path = join(folder, relative_path)
            if isdir(absolute_path):
                continue
            try:
                self.initialize_from_path(absolute_path)
            except (CrossComputeConfigurationError, CrossComputeDataError):
                raise
            except CrossComputeError:
                continue
            break
        else:
            raise CrossComputeConfigurationNotFoundError(
                'configuration not found')

    def initialize_from_path(self, path):
        configuration = load_configuration(path)
        self.path = path
        self.folder = configuration['folder']
        self.configuration = configuration
        self.definitions = get_automation_definitions(configuration)
        self._file_type_by_path = self._get_file_type_by_path()
        self._timestamp_object = Value('d', time())
        L.debug('configuration_path = %s', path)

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
            worker_process = LoggableProcess(
                name='worker', target=self.work, args=(automation_queue,))
            worker_process.daemon = True
            worker_process.start()
            L.info('serving at http://%s:%s%s', host, port, base_uri)
            # TODO: Decouple from pyramid and waitress
            app = self._get_app(
                automation_queue, is_static, is_production, base_uri)
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
        for automation_definition in self.definitions:
            for batch_definition in automation_definition.get('batches', []):
                run_automation(
                    automation_definition, batch_definition,
                    load_variable_data)

    def work(self, automation_queue):
        try:
            while automation_pack := automation_queue.get():
                run_automation(*automation_pack, load_variable_data)
        except KeyboardInterrupt:
            pass

    def watch(
            self, run_server, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds):
        server_process = StoppableProcess(name='server', target=run_server)
        server_process.start()
        for changes in watch(
                self.folder, min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            for changed_type, changed_path in changes:
                try:
                    file_type = self._get_file_type(changed_path)
                except KeyError:
                    continue
                L.debug('%s %s %s', changed_type, changed_path, file_type)
                if file_type == 'c':
                    try:
                        self.reload()
                    except CrossComputeError as e:
                        L.error(e)
                        continue
                    server_process.stop()
                    server_process = StoppableProcess(
                        name='server', target=run_server)
                    server_process.start()
                elif file_type == 's':
                    for d in self.definitions:
                        d['display'] = get_display_configuration(d)
                    self._timestamp_object.value = time()
                else:
                    self._timestamp_object.value = time()

    def _get_app(self, automation_queue, is_static, is_production, base_uri):
        automation_routes = AutomationRoutes(
            self.definitions, automation_queue, self._timestamp_object)
        stream_routes = StreamRoutes(self._timestamp_object)
        with Configurator(settings={
            'jinja2.trim_blocks': True,
            'jinja2.lstrip_blocks': True,
        }) as config:
            config.include('pyramid_jinja2')
            config.include(automation_routes.includeme)
            if not is_static:
                config.include(stream_routes.includeme)
            if not is_production:
                def update_cache_headers(e):
                    e.response.headers.update({'Cache-Control': 'no-store'})
                config.add_subscriber(update_cache_headers, NewResponse)

            def update_renderer_globals():
                renderer_environment = config.get_jinja2_environment()
                renderer_environment.globals.update({
                    'BASE_JINJA2': 'base.jinja2',
                    'LIVE_JINJA2': 'live.jinja2',
                    'IS_STATIC': is_static,
                    'IS_PRODUCTION': is_production,
                    'BASE_URI': base_uri,
                    'STREAMS_ROUTE': STREAMS_ROUTE,
                })
            config.action(None, update_renderer_globals)
        return config.make_wsgi_app()

    def _get_file_type(self, path):
        for automation_definition in self.definitions:
            automation_folder = automation_definition['folder']
            if is_path_in_folder(path, join(automation_folder, 'runs')):
                return 'v'
        return self._file_type_by_path[realpath(path)]

    def _get_file_type_by_path(self):
        'Set c = configuration, s = style, t = template, v = variable'
        file_type_by_path = {}

        def add(path, file_type):
            file_type_by_path[realpath(path)] = file_type

        for path in [self.path] + [_['path'] for _ in self.definitions]:
            add(path, 'c')
        for automation_definition in self.definitions:
            folder = automation_definition['folder']
            configuration = load_configuration(automation_definition['path'])
            for batch_definition in configuration.get('batches', []):
                batch_configuration = batch_definition.get('configuration', {})
                if 'path' not in batch_configuration:
                    continue
                add(join(folder, batch_configuration['path']), 'c')
            for mode_name in MODE_NAMES:
                mode_configuration = automation_definition.get(mode_name, {})
                template_definitions = mode_configuration.get('templates', [])
                for template_definition in template_definitions:
                    if 'path' not in template_definition:
                        continue
                    add(join(folder, template_definition['path']), 't')
            for batch_definition in automation_definition.get('batches', []):
                for path in self._get_paths_from_folder(join(
                        folder, batch_definition['folder'])):
                    add(path, 'v')
            display_configuration = automation_definition.get('display', {})
            for style_definition in display_configuration.get('styles', []):
                if 'path' not in style_definition:
                    continue
                add(join(folder, style_definition['path']), 's')
        return file_type_by_path

    def _get_paths_from_folder(self, folder):
        paths = set()
        for automation_definition in self.definitions:
            for mode_name in MODE_NAMES:
                mode_configuration = automation_definition.get(mode_name, {})
                variable_definitions = mode_configuration.get('variables', [])
                for variable_definition in variable_definitions:
                    variable_configuration = variable_definition.get(
                        'configuration', {})
                    if 'path' in variable_configuration:
                        paths.add(join(folder, variable_configuration['path']))
                    paths.add(join(folder, variable_definition['path']))
        return paths


def run_automation(
        automation_definition, batch_definition, process_data):
    script_definition = automation_definition.get('script', {})
    command_string = script_definition.get('command')
    if not command_string:
        return
    reference_time = time()
    folder = automation_definition['folder']
    batch_folder, custom_environment = _prepare_batch(
        automation_definition, batch_definition)
    L.info(
        '%s %s running %s', automation_definition['name'],
        automation_definition['version'],
        format_path(join(folder, batch_folder)))
    mode_folder_by_name = {_ + '_folder': make_folder(join(
        folder, batch_folder, _)) for _ in MODE_NAMES}
    script_environment = _prepare_script_environment(
        mode_folder_by_name, custom_environment)
    debug_folder = mode_folder_by_name['debug_folder']
    command_text = command_string.format(**mode_folder_by_name)
    command_folder = join(folder, script_definition.get('folder', '.'))
    return_code = _run_command(
        command_text, command_folder, script_environment,
        join(debug_folder, 'stdout.txt'), join(debug_folder, 'stderr.txt'))
    return _process_batch(automation_definition, batch_definition, [
        'output', 'log', 'debug',
    ], {'debug': {
        'execution_time_in_seconds': time() - reference_time,
        'return_code': return_code}}, process_data)


def _run_command(
        command_string, command_folder, script_environment, stdout_path,
        stderr_path):
    try:
        stdout_file = open(stdout_path, 'wt')
        stderr_file = open(stderr_path, 'w+t')
        process = subprocess.run(
            command_string,
            check=True,
            shell=True,  # Expand $HOME and ~ in command_string
            cwd=command_folder,
            env=script_environment,
            stdout=stdout_file,
            stderr=stderr_file)
        return_code = process.returncode
    except OSError as e:
        L.error(e)
        return_code = Error.COMMAND_NOT_FOUND
    except subprocess.CalledProcessError as e:
        stderr_file.seek(0)
        stderr_text = stderr_file.read().rstrip()
        L.error(stderr_text)
        return_code = e.returncode
    finally:
        stdout_file.close()
        stderr_file.close()
    return return_code


def _prepare_batch(automation_definition, batch_definition):
    variable_definitions = get_variable_definitions(
        automation_definition, 'input')
    batch_folder = batch_definition['folder']
    variable_definitions_by_path = group_by(variable_definitions, 'path')
    data_by_id = batch_definition.get('data_by_id', {})
    custom_environment = _prepare_custom_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    if not data_by_id:
        return batch_folder, custom_environment
    automation_folder = automation_definition['folder']
    input_folder = make_folder(join(automation_folder, batch_folder, 'input'))
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = join(input_folder, path)
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
    environment_variable_definitions = automation_definition.get(
        'environment', {}).get('variables', [])
    for variable_id in (_['id'] for _ in environment_variable_definitions):
        custom_environment[variable_id] = environ[variable_id]
    for variable_id in (_['id'] for _ in variable_definitions):
        if variable_id in data_by_id:
            continue
        try:
            custom_environment[variable_id] = environ[variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'{variable_id} is missing in the environment')
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id)
    variable_value_by_id = get_variable_value_by_id(variable_data_by_id)
    return custom_environment | variable_value_by_id


def _process_batch(
        automation_definition, batch_definition, mode_names,
        data_by_id_by_mode_name, process_data):
    variable_data_by_id_by_mode_name = {}
    automation_folder = automation_definition['folder']
    batch_folder = batch_definition['folder']
    for mode_name in mode_names:
        variable_data_by_id_by_mode_name[mode_name] = variable_data_by_id = {}
        data_by_id = data_by_id_by_mode_name.get(mode_name, {})
        mode_folder = join(automation_folder, batch_folder, mode_name)
        for variable_definition in get_variable_definitions(
                automation_definition, mode_name):
            variable_id = variable_definition['id']
            if variable_id in data_by_id:
                continue
            variable_path = variable_definition['path']
            path = join(mode_folder, variable_path)
            try:
                variable_data = process_data(path, variable_id)
            except CrossComputeDataError as e:
                L.error(e)
                continue
            variable_data_by_id[variable_id] = variable_data
        if data_by_id:
            update_variable_data(join(
                mode_folder, 'variables.dictionary'), data_by_id)
            variable_data_by_id.update(data_by_id)
    return variable_data_by_id_by_mode_name


L = getLogger(__name__)

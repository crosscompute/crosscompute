# TODO: Watch multiple folders if not all under parent folder
# TODO: Consider whether to send partial updates for variables
# TODO: Precompile notebook scripts
import logging
import shlex
import subprocess
from itertools import repeat
from logging import getLogger
from multiprocessing import Queue, Value
from os import environ, getenv
from pathlib import Path
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
    MUTATIONS_ROUTE,
    PING_INTERVAL_IN_SECONDS,
    PORT)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError,
    CrossComputeExecutionError)
from ..macros.iterable import group_by
from ..macros.process import LoggableProcess, StoppableProcess
from ..routes.automation import AutomationRoutes
from ..routes.mutation import MutationRoutes
from .configuration import (
    load_configuration)
from .interface import Automation
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

    def _reload(self):
        path = self.path
        if path.exists():
            self._initialize_from_path(path)
        else:
            self._initialize_from_folder(self.folder)

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
        self._file_code_by_path = self._get_file_code_by_path()
        self._timestamp_object = Value('d', time())

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
                automation_queue, is_static, is_production, base_uri,
                allowed_origins)
            try:
                serve(
                    app, host=host, port=port, url_prefix=base_uri, threads=8)
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
            batch_definitions = automation_definition.batch_definitions
            try:
                for batch_definition in batch_definitions:
                    _run_automation(
                        automation_definition, batch_definition,
                        load_variable_data)
            except CrossComputeError as e:
                e.automation_definition = automation_definition
                L.error(e)

    def work(self, automation_queue):
        try:
            while automation_pack := automation_queue.get():
                automation_definition, batch_definition = automation_pack
                try:
                    _run_automation(
                        automation_definition, batch_definition,
                        load_variable_data)
                except CrossComputeError as e:
                    e.automation_definition = automation_definition
                    L.error(e)
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
            should_restart_server = False
            for changed_type, changed_path in changes:
                try:
                    file_code = self._get_file_code(changed_path)
                except KeyError:
                    continue
                L.debug('%s %s %s', changed_type, changed_path, file_code)
                if file_code == 'c':
                    should_restart_server = True
            if should_restart_server:
                try:
                    self._reload()
                except CrossComputeError as e:
                    L.error(e)
                    continue
                server_process.stop()
                server_process = StoppableProcess(
                    name='server', target=run_server)
                server_process.start()
            else:
                self._timestamp_object.value = time()

    def _get_app(
            self, automation_queue, is_static, is_production, base_uri,
            allowed_origins):
        automation_routes = AutomationRoutes(
            self.configuration, self.definitions, automation_queue,
            self._timestamp_object)
        mutation_routes = MutationRoutes(self._timestamp_object)
        settings = {
            'base_uri': base_uri,
            'jinja2.trim_blocks': True,
            'jinja2.lstrip_blocks': True,
        }
        if not is_static and not is_production:
            settings.update({
                'pyramid.reload_templates': True,
            })
        with Configurator(settings=settings) as config:
            config.include('pyramid_jinja2')
            config.include(automation_routes.includeme)
            if not is_static:
                config.include(mutation_routes.includeme)
            _configure_renderer_globals(
                config, is_static, is_production, base_uri)
            _configure_cache_headers(config, is_production)
            _configure_allowed_origins(config, allowed_origins)
        return config.make_wsgi_app()

    def _get_file_code(self, path):
        path = Path(path)
        real_path = path.resolve()
        for automation_definition in self.definitions:
            automation_folder = automation_definition.folder
            runs_folder = automation_folder / 'runs'
            if not is_path_in_folder(path, runs_folder):
                continue
            run_id = path.absolute().relative_to(runs_folder).parts[0]
            run_folder = runs_folder / run_id
            expected_paths = self._get_variable_paths_from_folder(run_folder)
            for expected_path in expected_paths:
                if real_path == expected_path.resolve():
                    return 'v'
        return self._file_code_by_path[real_path]

    def _get_file_code_by_path(self):
        'Set c = configuration, s = style, t = template, v = variable'
        packs = []
        packs.extend(zip(self._get_configuration_paths(), repeat('c')))
        packs.extend(zip(self._get_variable_paths(), repeat('v')))
        packs.extend(zip(self._get_template_paths(), repeat('t')))
        packs.extend(zip(self._get_style_paths(), repeat('s')))
        return {path.resolve(): code for path, code in packs}

    def _get_configuration_paths(self):
        paths = set()
        # Get automation configuration paths
        paths.update([self.path] + [_.path for _ in self.definitions])
        # Get batch configuration paths
        for automation_definition in self.definitions:
            automation_folder = automation_definition.folder
            # Use raw batch definitions
            raw_batch_definitions = automation_definition.get('batches', [])
            for raw_batch_definition in raw_batch_definitions:
                batch_configuration = raw_batch_definition.get(
                    'configuration', {})
                if 'path' not in batch_configuration:
                    continue
                paths.add(automation_folder / batch_configuration['path'])
        return paths

    def _get_variable_paths(self):
        paths = set()
        for automation_definition in self.definitions:
            automation_folder = automation_definition.folder
            # Use computed batch definitions
            for batch_definition in automation_definition.batch_definitions:
                paths.update(self._get_variable_paths_from_folder(
                    automation_folder / batch_definition.folder))
        return paths

    def _get_template_paths(self):
        paths = set()
        for automation_definition in self.definitions:
            automation_folder = automation_definition.folder
            d = automation_definition.template_definitions_by_mode_name
            for template_definitions in d.values():
                for template_definition in template_definitions:
                    if 'path' not in template_definition:
                        continue
                    paths.add(automation_folder / template_definition.path)
            d = automation_definition.template_path_by_id
            for path in d.values():
                paths.add(automation_folder / path)
        return paths

    def _get_style_paths(self):
        paths = set()
        for automation_definition in self.definitions:
            automation_folder = automation_definition.folder
            for style_definition in automation_definition.style_definitions:
                if 'path' not in style_definition:
                    continue
                paths.add(automation_folder / style_definition['path'])
        return paths

    def _get_variable_paths_from_folder(self, absolute_batch_folder):
        paths = set()
        for automation_definition in self.definitions:
            d = automation_definition.variable_definitions_by_mode_name
            for mode_name, variable_definitions in d.items():
                folder = absolute_batch_folder / mode_name
                for variable_definition in variable_definitions:
                    variable_configuration = variable_definition.configuration
                    if 'path' in variable_configuration:
                        paths.add(folder / variable_configuration['path'])
                    paths.add(folder / variable_definition.path)
        return paths


def _run_automation(
        automation_definition, batch_definition, process_data):
    script_definitions = automation_definition.script_definitions
    if not script_definitions:
        return
    reference_time = time()
    folder = automation_definition.folder
    batch_folder, custom_environment = _prepare_batch(
        automation_definition, batch_definition)
    L.info(
        '%s %s running %s', automation_definition.name,
        automation_definition.version, format_path(folder / batch_folder))
    mode_folder_by_name = {_ + '_folder': make_folder(
        folder / batch_folder / _) for _ in MODE_NAMES}
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
        e.automation_definition = automation_definition
        L.error(e)
        return_code = e.return_code
    return _process_batch(automation_definition, batch_definition, [
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


def _configure_cache_headers(config, is_production):
    if is_production:
        return

    def update_cache_headers(e):
        e.response.headers.update({'Cache-Control': 'no-store'})

    config.add_subscriber(update_cache_headers, NewResponse)


def _configure_allowed_origins(config, allowed_origins):
    if not allowed_origins:
        return

    def update_cors_headers(e):
        request_headers = e.request.headers
        if 'Origin' not in request_headers:
            return
        origin = request_headers['Origin']
        if origin not in allowed_origins:
            return
        e.response.headers.update({
            'Access-Control-Allow-Origin': origin})

    config.add_subscriber(update_cors_headers, NewResponse)


def _configure_renderer_globals(config, is_static, is_production, base_uri):

    def update_renderer_globals():
        config.get_jinja2_environment().globals.update({
            'BASE_JINJA2': 'crosscompute:templates/base.jinja2',
            'LIVE_JINJA2': 'crosscompute:templates/live.jinja2',
            'IS_STATIC': is_static,
            'IS_PRODUCTION': is_production,
            'BASE_URI': base_uri,
            'MUTATIONS_ROUTE': MUTATIONS_ROUTE,
            'PING_INTERVAL_IN_MILLISECONDS': PING_INTERVAL_IN_SECONDS * 1000,
        })

    config.action(None, update_renderer_globals)


L = getLogger(__name__)

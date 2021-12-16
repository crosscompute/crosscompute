# TODO: Send refresh without server restart for template changes
import logging
import subprocess
from logging import getLogger
from multiprocessing import Value
from os import getenv, listdir
from os.path import isdir, join, relpath, splitext
from pyramid.config import Configurator
from time import time
from waitress import serve
from watchgod import watch

from .configuration import (
    get_automation_definitions,
    get_display_configuration,
    get_raw_variable_definitions,
    load_configuration,
    make_automation_name,
    prepare_batch_folder)
from ..constants import (
    CONFIGURATION_EXTENSIONS,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT,
    STYLE_EXTENSIONS,
    TEMPLATE_EXTENSIONS)
from ..exceptions import CrossComputeError, CrossComputeConfigurationError
from ..macros import StoppableProcess, format_path, make_folder
from ..views import AutomationViews, EchoViews


L = getLogger(__name__)


class Automation():

    def initialize_from_path(self, configuration_path):
        configuration = load_configuration(configuration_path)
        configuration_folder = configuration['folder']
        automation_definitions = get_automation_definitions(
            configuration)

        self.configuration_path = configuration_path
        self.configuration = configuration
        self.configuration_folder = configuration_folder
        self.automation_definitions = automation_definitions
        self.timestamp_object = Value('d', time())

        L.debug('configuration_path = %s', configuration_path)
        L.debug('configuration_folder = %s', configuration_folder)

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        if isdir(path_or_folder):
            for path in listdir(path_or_folder):
                try:
                    instance.initialize_from_path(path)
                except CrossComputeConfigurationError:
                    raise
                except CrossComputeError:
                    continue
                break
            else:
                raise CrossComputeError('could not find configuration')
        else:
            instance.initialize_from_path(path_or_folder)
        return instance

    def run(self, custom_environment=None):
        for automation_index, automation_definition in enumerate(
                self.automation_definitions):
            automation_name = automation_definition.get(
                'name', make_automation_name(automation_index))
            script_definition = automation_definition.get('script', {})
            command_string = script_definition.get('command')
            if not command_string:
                L.warning(f'{automation_name} script command not defined')
                continue
            automation_folder = automation_definition['folder']
            script_folder = script_definition.get('folder', '.')
            input_variable_definitions = get_raw_variable_definitions(
                automation_definition, 'input')
            # TODO: Load base custom environment from configuration
            for batch_definition in automation_definition.get('batches', []):
                batch_folder = prepare_batch_folder(
                    batch_definition, input_variable_definitions,
                    automation_folder)
                L.info(f'{automation_name} running {batch_folder}')
                run_batch(
                    batch_folder, command_string, script_folder,
                    automation_folder, custom_environment)

    def serve(
            self,
            host=HOST,
            port=PORT,
            base_uri='',
            is_production=False,
            is_static=False,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
        if getLogger().level > logging.DEBUG:
            getLogger('waitress').setLevel(logging.ERROR)
            getLogger('watchgod.watcher').setLevel(logging.ERROR)

        def run_server():
            L.info(f'serving at http://{host}:{port}{base_uri}')
            app = self.get_app(is_static, base_uri)
            try:
                serve(app, host=host, port=port, url_prefix=base_uri)
            except OSError as e:
                L.error(e)

        if is_production and is_static:
            run_server()
            return

        server_process = StoppableProcess(target=run_server)
        server_process.start()
        for changes in watch(
                self.configuration_folder,
                min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            for changed_type, changed_path in changes:
                # TODO: Continue only if path is in configuration
                L.debug('%s %s', changed_type, changed_path)
                changed_extension = splitext(changed_path)[1]
                if changed_extension in CONFIGURATION_EXTENSIONS:
                    server_process.stop()
                    self.initialize_from_path(self.configuration_path)
                    server_process = StoppableProcess(target=run_server)
                    server_process.start()
                elif changed_extension in STYLE_EXTENSIONS:
                    for d in self.automation_definitions:
                        d['display'] = get_display_configuration(d)
                    self.timestamp_object.value = time()
                elif changed_extension in TEMPLATE_EXTENSIONS:
                    self.timestamp_object.value = time()

    def get_app(self, is_static=False, base_uri=''):
        # TODO: Decouple from pyramid
        automation_views = AutomationViews(
            self.automation_definitions)
        echo_views = EchoViews(
            self.configuration_folder, self.timestamp_object)
        with Configurator() as config:
            config.include('pyramid_jinja2')
            config.include(automation_views.includeme)
            if not is_static:
                config.include(echo_views.includeme)

            def update_renderer_globals():
                renderer_environment = config.get_jinja2_environment()
                renderer_environment.globals.update({
                    'BASE_URI': base_uri,
                    'IS_STATIC': is_static,
                })

            config.action(None, update_renderer_globals)
        return config.make_wsgi_app()


def run_batch(
        batch_folder, command_string, script_folder, configuration_folder,
        custom_environment=None):
    input_folder = join(batch_folder, 'input')
    output_folder = join(batch_folder, 'output')
    log_folder = join(batch_folder, 'log')
    debug_folder = join(batch_folder, 'debug')
    run_script(
        command_string, script_folder, input_folder, output_folder,
        log_folder, debug_folder, configuration_folder,
        custom_environment)


def run_script(
        command_string, script_folder, input_folder, output_folder,
        log_folder, debug_folder, configuration_folder,
        custom_environment=None):
    # TODO: Make each folder optional
    default_environment = {
        'CROSSCOMPUTE_INPUT_FOLDER': relpath(
            input_folder, script_folder),
        'CROSSCOMPUTE_OUTPUT_FOLDER': relpath(
            output_folder, script_folder),
        'CROSSCOMPUTE_LOG_FOLDER': relpath(
            log_folder, script_folder),
        'CROSSCOMPUTE_DEBUG_FOLDER': relpath(
            debug_folder, script_folder),
        'PATH': getenv('PATH', ''),
    }
    environment = default_environment | (custom_environment or {})
    L.debug('environment = %s', environment)

    for folder_label, relative_folder in {
        'input': input_folder,
        'output': output_folder,
        'log': log_folder,
        'debug': debug_folder,
    }.items():
        folder = make_folder(join(configuration_folder, relative_folder))
        L.debug(f'{folder_label}_folder = {format_path(folder)}')

    # TODO: Capture stdout and stderr for live output
    subprocess.run(
        command_string,
        shell=True,
        cwd=join(configuration_folder, script_folder),
        env=environment)

# TODO: Be explicit about relative vs absolute folders
# TODO: Precompile notebook scripts
import logging
import subprocess
from logging import getLogger
from multiprocessing import Process, Queue, Value
from os import getenv, listdir
from os.path import isdir, join, relpath, splitext
from pyramid.config import Configurator
from time import time
from waitress import serve
from watchgod import watch

from .configuration import (
    format_text,
    get_automation_definitions,
    get_display_configuration,
    load_configuration,
    make_automation_name,
    prepare_batch)
from ..constants import (
    CONFIGURATION_EXTENSIONS,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT,
    STYLE_EXTENSIONS,
    # TEMPLATE_EXTENSIONS,
)
from ..exceptions import CrossComputeError, CrossComputeConfigurationError
from ..macros import StoppableProcess, format_path, make_folder
from ..views import AutomationViews, EchoViews


L = getLogger(__name__)


class Automation():

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
            for batch_definition in automation_definition.get('batches', []):
                batch_folder, custom_environment = prepare_batch(
                    automation_definition, batch_definition)
                run_batch(
                    batch_folder, command_string, script_folder,
                    automation_folder, custom_environment)

    def serve(
            self,
            host=HOST,
            port=PORT,
            base_uri='',
            is_static=False,
            is_production=False,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS,
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
            L.info(f'serving at http://{host}:{port}{base_uri}')
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

    def get_app(self, automation_queue, is_static=False, base_uri=''):
        # TODO: Decouple from pyramid
        automation_views = AutomationViews(
            self.automation_definitions,
            automation_queue,
            self.timestamp_object)
        echo_views = EchoViews(
            self.automation_folder,
            self.timestamp_object)
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

    def work(self, automation_queue):
        try:
            while automation_pack := automation_queue.get():
                automation_definition, batch_definition = automation_pack
                run_automation(automation_definition, batch_definition)
        except KeyboardInterrupt:
            pass

    def watch(
            self, run_server, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds):
        server_process = StoppableProcess(target=run_server)
        server_process.start()
        for changes in watch(
                self.automation_folder,
                min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            for changed_type, changed_path in changes:
                # TODO: Continue only if path is in the configuration
                # TODO: Continue only if the file hash has changed
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
                # elif changed_extension in TEMPLATE_EXTENSIONS:
                    # self.timestamp_object.value = time()
                else:
                    # TODO: Send partial updates
                    self.timestamp_object.value = time()


def run_automation(automation_definition, batch_definition):
    batch_folder, custom_environment = prepare_batch(
        automation_definition, batch_definition)
    script_definition = automation_definition.get('script', {})
    command_string = script_definition.get('command')
    script_folder = script_definition.get('folder', '.')
    automation_folder = automation_definition['folder']
    run_batch(
        batch_folder, command_string, script_folder, automation_folder,
        custom_environment)


def run_batch(
        batch_folder, command_string, script_folder, automation_folder,
        custom_environment):
    L.info(f'running {format_path(join(automation_folder, batch_folder))}')
    run_script(
        command_string,
        script_folder,
        join(batch_folder, 'input'),
        join(batch_folder, 'output'),
        join(batch_folder, 'log'),
        join(batch_folder, 'debug'),
        automation_folder,
        custom_environment)
    part_folder_by_name = { for part_name in PART_TYPE_NAMES}


def run_script(
        command_string, script_folder, input_folder, output_folder, log_folder,
        debug_folder, automation_folder, custom_environment):
    part_folder_by_name = {k: join(automation_folder, v) for k, v in {
        'input_folder': input_folder,
        'output_folder': output_folder,
        'log_folder': log_folder,
        'debug_folder': debug_folder,
    }.items()}

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
    environment = default_environment | custom_environment
    L.debug('environment = %s', environment)

    part_folder_by_name = kkkkkkkkk{
    {k: relpath(v, script_folder) for k, v in part_folder_by_name.items()}
    for folder_name, part_folder in part_folder_by_name.items():
        make_folder(join(automation_folder, part_folder))

    # TODO: Capture stdout and stderr in debug_folder
    subprocess.run(
        format_text(command_string, part_folder_by_name),
        shell=True,
        cwd=join(automation_folder, script_folder),
        env=environment)

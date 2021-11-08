import logging
import subprocess
import yaml
from multiprocessing import Process
from os import getenv
from os.path import dirname, join, relpath, splitext
from pyramid.config import Configurator
from waitress import serve
from watchgod import watch

from ..constants import HOST, PORT
from ..macros import format_path, make_folder
from ..views import AutomationViews, EchoViews


class Automation():

    @classmethod
    def load(Class, configuration_path):
        configuration = yaml.safe_load(open(configuration_path, 'rt'))
        script_definition = configuration['script']
        configuration_folder = dirname(configuration_path)
        command_string = script_definition['command']

        instance = Class()
        instance.configuration_path = configuration_path
        instance.configuration_folder = configuration_folder
        instance.configuration = configuration
        instance.script_folder = script_definition['folder']
        instance.command_string = command_string
        instance.automation_views = AutomationViews(
            configuration, configuration_folder)
        instance.echo_views = EchoViews(
            configuration_folder)

        logging.debug('configuration_folder = %s', configuration_folder)
        logging.debug('command_string = %s', command_string)
        return instance

    def run(self, custom_environment=None):
        # TODO: Load base custom environment from configuration
        for batch_definition in self.configuration['batches']:
            batch_folder = batch_definition['folder']
            self.run_batch(batch_folder, custom_environment)

    def run_batch(self, batch_folder, custom_environment=None):
        # TODO: Consider accepting batch_name
        input_folder = join(batch_folder, 'input')
        output_folder = join(batch_folder, 'output')
        log_folder = join(batch_folder, 'log')
        debug_folder = join(batch_folder, 'debug')
        self.run_script(
            input_folder, output_folder, log_folder, debug_folder,
            custom_environment)

    def run_script(
            self, input_folder, output_folder, log_folder, debug_folder,
            custom_environment=None):
        # TODO: Make each folder optional
        default_environment = {
            'CROSSCOMPUTE_INPUT_FOLDER': relpath(
                input_folder, self.script_folder),
            'CROSSCOMPUTE_OUTPUT_FOLDER': relpath(
                output_folder, self.script_folder),
            'CROSSCOMPUTE_LOG_FOLDER': relpath(
                log_folder, self.script_folder),
            'CROSSCOMPUTE_DEBUG_FOLDER': relpath(
                debug_folder, self.script_folder),
            'PATH': getenv('PATH', ''),
        }
        environment = default_environment | (custom_environment or {})
        logging.debug('environment = %s', environment)

        for folder_label, relative_folder in {
            'input': input_folder,
            'output': output_folder,
            'log': log_folder,
            'debug': debug_folder,
        }.items():
            folder = make_folder(join(
                self.configuration_folder, relative_folder))
            logging.info(f'{folder_label}_folder = {format_path(folder)}')

        # TODO: Capture stdout and stderr for live output
        subprocess.run(
            self.command_string,
            shell=True,
            cwd=self.configuration_folder,
            env=environment)

    def serve(
            self,
            host=HOST,
            port=PORT,
            is_production=False,
            is_static=False):
        with Configurator() as config:
            config.include('pyramid_jinja2')
            config.include(self.automation_views.includeme)
            if not is_static:
                config.include(self.echo_views.includeme)
        app = config.make_wsgi_app()

        def run_server():
            # TODO: Reload automation if configuration changed
            # TODO: Search for configuration if the file is gone
            print('run_server')
            serve(app, host=host, port=port)

        def handle_changes(changes):
            # TODO: move this to class
            print('handle_changes', changes)
            self.echo_views.queue.put('*')
            # import time; time.sleep(1)

        if is_production:
            run_server()
            return

        server_process = Process(target=run_server)
        server_process.start()
        for changes in watch(self.configuration_folder):
            for changed_type, changed_path in changes:
                changed_extension = splitext(changed_path)[1]
                print(changed_type, changed_path, changed_extension)
                if changed_extension in ['.yml']:
                    print('SERVER RESTART')
                    server_process.terminate()
                    # !!! might need to join here
                    server_process = Process(target=run_server)
                    server_process.start()

        '''
        run_process(
            self.configuration_folder,
            run_server,
            callback=handle_changes,
            watcher_cls=DefaultWatcher)
        '''

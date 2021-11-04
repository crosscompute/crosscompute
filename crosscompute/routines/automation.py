import logging
import subprocess
import yaml
from os import getenv
from os.path import dirname, join, relpath

from ..macros import format_path, make_folder


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

    def serve(self):
        pass

# TODO: Separate configuration validation
# TODO: Support case when user does not specify configuration file
# TODO: Improve output when running batches
# TODO: Separate run_batch(batch_folder) into a function
import subprocess
import yaml
from os import getenv
from os.path import dirname, join, relpath
from sys import argv


if __name__ == '__main__':
    configuration_path = argv[1]
    configuration_folder = dirname(configuration_path)
    configuration = yaml.safe_load(open(configuration_path, 'rt'))
    print(configuration)

    script_definition = configuration['script']
    script_folder = script_definition['folder']
    command_string = script_definition['command']

    for batch_definition in configuration['batches']:
        print(batch_definition)

        batch_folder = batch_definition['folder']
        input_folder = join(batch_folder, 'input')
        output_folder = join(batch_folder, 'output')

        command_environment = {
            'PATH': getenv('PATH', ''),
            'CROSSCOMPUTE_INPUT_FOLDER': relpath(
                input_folder, script_folder),
            'CROSSCOMPUTE_OUTPUT_FOLDER': relpath(
                output_folder, script_folder),
        }

        print(command_string)
        print(command_environment)

        subprocess.run(
            command_string,
            shell=True,
            cwd=configuration_folder,
            env=command_environment)

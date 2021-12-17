from crosscompute.routines.automation import Automation, run_batch
from crosscompute.routines.configuration import (
    get_raw_variable_definitions, prepare_batch_folder)
from os.path import expanduser, join
# from sys import argv


# configuration_path = argv[1]
examples_folder = expanduser('~/Projects/crosscompute-examples')
configuration_path = join(examples_folder, 'tools/add-numbers/automate.yml')
automation = Automation.load(configuration_path)
automation_definition = automation.automation_definitions[0]
# batch_definition = automation_definition['batches'][0]
batch_definition = {
    'folder': '/tmp/aaa',
    'data_by_id': {'a': 1, 'b': 2},
}
configuration = automation.configuration
variable_definitions = get_raw_variable_definitions(configuration, 'input')
configuration_folder = automation.configuration_folder
script_definition = automation_definition.get('script', {})
command_string = script_definition.get('command')
automation_folder = automation_definition['folder']
script_folder = script_definition.get('folder', '.')
batch_folder = prepare_batch_folder(
    batch_definition, variable_definitions, configuration_folder)
run_batch(
    batch_folder, command_string, script_folder, configuration_folder,
    custom_environment=None)

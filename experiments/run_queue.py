from crosscompute.routines.automation import Automation, run_batch
from crosscompute.routines.configuration import (
    get_raw_variable_definitions, prepare_batch_folder)
from multiprocessing import Process, Queue
from os.path import expanduser, join


def process_automation_queue(automation_queue):
    while automation_pack := automation_queue.get():
        automation_definition, batch_definition = automation_pack
        print(batch_definition)
        variable_definitions = get_raw_variable_definitions(
            automation_definition, 'input')
        configuration_folder = automation_definition['folder']
        batch_folder = prepare_batch_folder(
            batch_definition, variable_definitions, configuration_folder)
        script_definition = automation_definition.get('script', {})
        command_string = script_definition.get('command')
        script_folder = script_definition.get('folder', '.')
        run_batch(
            batch_folder, command_string, script_folder, configuration_folder,
            custom_environment=None)


examples_folder = expanduser('~/Projects/crosscompute-examples')
configuration_path = join(examples_folder, 'tools/add-numbers/automate.yml')
automation = Automation.load(configuration_path)
automation_definition = automation.automation_definitions[0]


automation_queue = Queue()
process = Process(target=process_automation_queue, args=(automation_queue,))
process.start()
automation_queue.put((
    automation_definition,
    {'folder': '/tmp/a1', 'data_by_id': {'a': 1, 'b': 1}}))
automation_queue.put((
    automation_definition,
    {'folder': '/tmp/a2', 'data_by_id': {'a': 1, 'b': 2}}))
automation_queue.put((
    automation_definition,
    {'folder': '/tmp/a3', 'data_by_id': {'a': 1, 'b': 3}}))

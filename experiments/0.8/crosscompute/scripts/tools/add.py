from os import chdir, environ
from os.path import join

from .. import OutputtingScript, run_safely
from ...constants import TOOL_FILE_NAME
from ...routines import (
    fetch_resource,
    get_bash_configuration_text,
    load_relevant_path,
    prepare_dataset,
    process_result_definition,
    run_tests,
    run_worker)


class AddToolScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock',
            help='perform dry run')
        argument_subparser.add_argument(
            '--work', action='store_true', dest='with_worker',
            help='run worker after adding tool')
        argument_subparser.add_argument(
            'tool_definition_path',
            metavar='TOOL_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        tool_definition = run_safely(load_relevant_path, {
            'path': args.tool_definition_path,
            'name': TOOL_FILE_NAME,
            'kinds': ['tool'],
        }, is_quiet, as_json)

        result_dictionaries = run_safely(run_tests, {
            'tool_definition': tool_definition,
        }, is_quiet, as_json)['results']

        if args.is_mock:
            return

        d = run_safely(fetch_resource, {
            'resource_name': 'tools',
            'resource_id': None,
            'method': 'POST',
            'data': tool_definition,
        }, is_quiet, as_json)

        for result_dictionary in result_dictionaries:
            result_dictionary = process_result_definition(
                result_dictionary, tool_definition, prepare_dataset)
            result_dictionary['tool'] = tool_definition
            run_safely(fetch_resource, {
                'resource_name': 'results',
                'resource_id': None,
                'method': 'POST',
                'data': result_dictionary,
            }, is_quiet, as_json)

        environ['CROSSCOMPUTE_TOKEN'] = d['token']
        tool_definition_folder = tool_definition['folder']
        script_folder = join(
            tool_definition_folder, tool_definition['script']['folder'])
        if not is_quiet and not as_json:
            print('\n' + get_bash_configuration_text())
            print(f'cd {script_folder}')
            print('crosscompute workers run')
        if args.with_worker:
            chdir(tool_definition_folder)
            run_safely(run_worker, {
                'with_tests': False,
            }, is_quiet, as_json)

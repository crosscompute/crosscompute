from os import environ
from os.path import join

from .. import OutputtingScript, run_safely
from ...constants import TOOL_FILE_NAME
from ...routines import (
    fetch_resource,
    get_bash_configuration_text,
    load_relevant_path,
    run_tests)


class AddToolScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'tool_definition_path',
            metavar='TOOL_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        tool_definition = run_safely(load_relevant_path, [
            args.tool_definition_path, TOOL_FILE_NAME, ['tool'],
        ], is_quiet, as_json)

        run_safely(run_tests, [
            tool_definition,
        ], is_quiet, as_json)

        if args.is_mock:
            return
        d = run_safely(fetch_resource, [
            'tools', None, 'POST', tool_definition,
        ], is_quiet, as_json)
        environ['CROSSCOMPUTE_TOKEN'] = d['token']
        script_folder = join(
            tool_definition['folder'], tool_definition['script']['folder'])
        if not is_quiet and not as_json:
            print('\n' + get_bash_configuration_text())
            print(f'cd {script_folder}')
            print('crosscompute workers run')

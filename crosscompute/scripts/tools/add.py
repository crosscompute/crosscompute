from os import environ

from .. import OutputtingScript, run_safely
from ...constants import TOOL_FILE_NAME
from ...routines import (
    fetch_resource,
    get_bash_configuration_text,
    load_relevant_path,
    run_worker)


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
            args.tool_definition_path,
            TOOL_FILE_NAME,
            ['tool'],
        ], is_quiet, as_json)

        if args.is_mock:
            return
        if not is_quiet and not as_json:
            print('---')
        d = run_safely(fetch_resource, [
            'tools', None, 'POST', tool_definition,
        ], is_quiet, as_json)
        environ['CROSSCOMPUTE_TOKEN'] = d['token']
        if not is_quiet and not as_json:
            script_command = d.get('script', {}).get('command', '')
            print('\n' + get_bash_configuration_text())
            print('crosscompute workers run ' + script_command)
        run_safely(run_worker, [], is_quiet, as_json)

from os import environ

from .. import OutputtingScript
from ...exceptions import CrossComputeError
from ...routines import (
    fetch_resource,
    get_bash_configuration_text,
    get_server_url,
    load_definition,
    render_object,
    run_safely,
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
        tool_definition_path = args.tool_definition_path
        as_json = args.as_json
        is_quiet = args.is_quiet

        try:
            tool_dictionary = load_definition(
                tool_definition_path, kinds=['tool'])
        except CrossComputeError as e:
            if is_quiet:
                exit(1)
            exit(render_object(e.args[0], as_json))

        if args.is_mock:
            if not is_quiet:
                print(render_object(tool_dictionary, as_json))
            return
        d = run_safely(fetch_resource, [
            'tools', None, 'POST', tool_dictionary,
        ], as_json, is_quiet)

        environ['CROSSCOMPUTE_TOKEN'] = token = d['token']
        if not is_quiet and not as_json:
            script_dictionary = d.get('script', {})
            script_command = script_dictionary.get('command', '')
            print('\n' + get_bash_configuration_text(token))
            print('crosscompute workers run ' + script_command)
        run_safely(run_worker, [
            get_server_url(),
            token,
            as_json,
            is_quiet,
        ], as_json, is_quiet)

from .. import OutputtingScript
from ...exceptions import CrossComputeError
from ...routines import (
    add_tool,
    get_bash_configuration_text,
    load_definition,
    render_object,
    run_safely)


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
        d = run_safely(add_tool, [
            tool_dictionary,
        ], as_json, is_quiet)

        if is_quiet:
            return
        print(render_object(d, as_json))
        if not as_json:
            tool_version_dictionary = d['versions'][0]
            script_dictionary = d.get('script', {})
            token = tool_version_dictionary['token']
            script_command = script_dictionary.get('command', '')
            print('\n' + get_bash_configuration_text(token))
            print('crosscompute workers run ' + script_command)

        # TODO: Consider running worker

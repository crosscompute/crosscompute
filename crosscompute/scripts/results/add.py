from .. import OutputtingScript
from ...exceptions import CrossComputeError
from ...routines import (
    add_result,
    load_definition,
    render_object,
    run_safely)


class AddResultScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'result_definition_path',
            metavar='RESULT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        result_definition_path = args.result_definition_path
        as_json = args.as_json
        is_quiet = args.is_quiet

        try:
            result_dictionary = load_definition(
                result_definition_path, kinds=['result'])
        except CrossComputeError as e:
            if is_quiet:
                exit(1)
            exit(render_object(e.args[0], as_json))

        if args.is_mock:
            print(render_object(result_dictionary, as_json))
            return
        d = run_safely(add_result, [
            result_dictionary,
        ], as_json, is_quiet)

        if is_quiet:
            return
        print(render_object(d, as_json))

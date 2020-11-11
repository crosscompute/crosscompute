from .. import OutputtingScript
from ...routines import fetch_resource, run_safely


class SeeResultScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'result_id', metavar='RESULT_ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(fetch_resource, [
            'results', args.result_id,
        ], args.as_json, args.is_quiet)

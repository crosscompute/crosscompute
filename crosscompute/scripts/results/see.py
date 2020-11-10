from .. import OutputtingScript
from ...routines import run_safely, see_results


class SeeResultScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'result_ids', metavar='RESULT-ID', nargs='*')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(see_results, [
            args.result_ids,
        ], args.as_json, args.is_quiet)

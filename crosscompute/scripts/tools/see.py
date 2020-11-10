from .. import OutputtingScript
from ...routines import run_safely, see_tools


class SeeToolScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'tool_ids', metavar='TOOL_ID', nargs='*')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(see_tools, [
            args.tool_ids,
        ], args.as_json, args.is_quiet)

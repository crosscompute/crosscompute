from .. import OutputtingScript
from ...routines import fetch_resource, run_safely


class SeeToolScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'tool_id', metavar='TOOL_ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(fetch_resource, [
            'tools', args.tool_id,
        ], args.as_json, args.is_quiet)

from .. import OutputtingScript, run_safely
from ...routines import fetch_resource


class SeeToolScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'tool_id', metavar='TOOL_ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        run_safely(fetch_resource, {
            'resource_name': 'tools',
            'resource_id': args.tool_id,
        }, is_quiet, as_json)

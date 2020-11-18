from .. import OutputtingScript, run_safely
from ...routines import fetch_resource


class SeeProjectsScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'project_id', metavar='PROJECT_ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        run_safely(fetch_resource, [
            'projects', args.project_id,
        ], is_quiet, as_json)

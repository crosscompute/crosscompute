from .. import OutputtingScript
from ...routines import fetch_resource, run_safely


class SeeProjectsScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'project_id', metavar='PROJECT_ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(fetch_resource, [
            'projects', args.project_id,
        ], args.as_json, args.is_quiet)

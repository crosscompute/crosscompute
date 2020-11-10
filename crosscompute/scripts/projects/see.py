from .. import OutputtingScript
from ...routines import run_safely, see_projects


class SeeProjectsScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'project_ids', metavar='PROJECT_ID', nargs='*')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(see_projects, [
            args.project_ids,
        ], args.as_json, args.is_quiet)

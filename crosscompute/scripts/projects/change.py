from .. import OutputtingScript
from ...routines import change_project, run_safely


class ChangeProjectScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'project_id', metavar='PROJECT_ID')
        argument_subparser.add_argument(
            '--name', metavar='PROJECT_NAME',
            dest='project_name')
        argument_subparser.add_argument(
            '--toolId', metavar='TOOL_ID', action='append',
            dest='tool_ids')
        argument_subparser.add_argument(
            '--resultId', metavar='RESULT_ID', action='append',
            dest='result_ids')
        argument_subparser.add_argument(
            '--datasetId', metavar='DATASET_ID', action='append',
            dest='dataset_ids')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(change_project, [
            args.project_id,
            args.project_name,
            args.tool_ids or [],
            args.result_ids or [],
            args.dataset_ids or [],
        ], args.as_json, args.is_quiet)

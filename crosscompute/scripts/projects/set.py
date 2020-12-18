from .. import OutputtingScript, run_safely
from ...constants import PROJECT_FILE_NAME
from ...routines import (
    fetch_resource,
    load_relevant_path)


class SetProjectScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock',
            help='perform dry run')
        argument_subparser.add_argument(
            'project_definition_path',
            metavar='PROJECT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        project_definition = run_safely(load_relevant_path, {
            'path': args.project_definition_path,
            'name': PROJECT_FILE_NAME,
            'kinds': ['project'],
        }, is_quiet, as_json)
        project_id = project_definition.get('id')

        run_safely(fetch_resource, {
            'resource_name': 'projects',
            'resource_id': project_id,
            'method': 'PATCH' if project_id else 'POST',
            'data': project_definition,
        }, is_quiet, as_json)

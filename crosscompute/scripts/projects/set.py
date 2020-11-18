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

        project_definition = run_safely(load_relevant_path, [
            args.project_definition_path,
            PROJECT_FILE_NAME,
            ['project'],
        ], is_quiet, as_json)
        project_id = project_definition.get('id')

        run_safely(fetch_resource, [
            'projects', project_id,
            'PATCH' if project_id else 'POST',
            project_definition,
        ], is_quiet, as_json)

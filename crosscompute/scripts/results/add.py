from .. import OutputtingScript, run_safely
from ...constants import RESULT_FILE_NAME
from ...routines import (
    fetch_resource,
    load_relevant_path)


class AddResultScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'result_definition_path',
            metavar='RESULT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        result_definition = run_safely(load_relevant_path, {
            'path': args.result_definition_path,
            'name': RESULT_FILE_NAME,
            'kinds': ['result'],
        }, is_quiet, as_json)

        if args.is_mock:
            return
        run_safely(fetch_resource, {
            'resource_name': 'results',
            'resource_id': None,
            'method': 'POST',
            'data': result_definition,
        }, is_quiet, as_json)

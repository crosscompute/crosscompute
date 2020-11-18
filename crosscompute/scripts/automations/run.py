from .. import OutputtingScript, run_safely
from ...constants import AUTOMATION_FILE_NAME
from ...routines import load_relevant_path, run_automation


class RunAutomationScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock',
            help='perform dry run')
        argument_subparser.add_argument(
            'automation_definition_path',
            metavar='AUTOMATION_DEFINITION_PATH', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        automation_definition = run_safely(load_relevant_path, [
            args.automation_definition_path,
            AUTOMATION_FILE_NAME,
            ['automation'],
        ], is_quiet, as_json)

        run_safely(run_automation, [
            automation_definition,
            args.is_mock,
        ], is_quiet, as_json)

from .. import OutputtingScript
from ...routines import run_automation, run_safely


class RunAutomationScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'automation_definition_path',
            metavar='AUTOMATION_DEFINITION_PATH', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        as_json = args.as_json
        is_quiet = args.is_quiet
        run_safely(run_automation, [
            args.automation_definition_path or '.',
            args.is_mock,
        ], as_json, is_quiet)

from .. import OutputtingScript
from ...routines import (
    run_automation,
    run_safely)


class RunAutomationScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'path', metavar='AUTOMATION_DEFINITION_PATH', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        run_safely(run_automation, [
            args.path or '.',
            args.is_mock,
        ], args.as_json, args.is_quiet)

from invisibleroads.scripts import LoggingScript

from ...routines import run_automation


class RunAutomationScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('path', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        return run_automation(args.path or '.')

from invisibleroads.scripts import LoggingScript

from ...constants import AUTOMATION_FILE_NAME
from ...exceptions import CrossComputeExecutionError
from ...routines import find_relevant_path


class RunAutomationScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('path', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        return run(args.path or '.')


def run(path):
    try:
        automation_path = find_relevant_path(
            path, AUTOMATION_FILE_NAME)
    except OSError:
        raise CrossComputeExecutionError({'automation': 'is missing'})
    print(automation_path)

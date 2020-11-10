import sys
from argparse import RawDescriptionHelpFormatter
from invisibleroads.scripts import LoggingScript, launch_script

from .. import __description__
from ..routines import get_bash_configuration_text


class OutputtingScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--json', action='store_true',
            dest='as_json',
            help='render output as json')


def launch(argv=sys.argv):
    launch_script(
        'crosscompute',
        argv,
        description=__description__,
        epilogue=get_bash_configuration_text(),
        formatter_class=RawDescriptionHelpFormatter)

import logging
import sys
from invisibleroads.scripts import Script, launch_script


# TODO: Move to invisibleroads package
class LoggingScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('--quiet', action='store_true')

    def run(self, args, argv):
        if args.quiet:
            return
        logging.basicConfig()


def launch(argv=sys.argv):
    launch_script('crosscompute', argv)

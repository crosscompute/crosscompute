import sys
from invisibleroads.scripts import LoggingScript, launch_script

from ..routines import get_crosscompute_host, get_crosscompute_token


class AuthenticatingScript(LoggingScript):

    def run(self, args, argv):
        super().run(args, argv)
        args.host = get_crosscompute_host()
        args.token = get_crosscompute_token()


def launch(argv=sys.argv):
    launch_script('crosscompute', argv)

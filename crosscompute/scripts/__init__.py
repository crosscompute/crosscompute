import sys
from invisibleroads.scripts import LoggingScript, launch_script

from ..routines import get_server_url, get_token


class AuthenticatingScript(LoggingScript):

    def run(self, args, argv):
        super().run(args, argv)
        args.server_url = get_server_url()
        args.token = get_token()


def launch(argv=sys.argv):
    launch_script('crosscompute', argv)

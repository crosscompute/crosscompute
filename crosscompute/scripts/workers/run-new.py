from .. import AuthenticatingScript
from ...routines import get_echoes_client


class RunWorkerScript(AuthenticatingScript):

    def run(self, args, argv):
        super().run(args, argv)
        return run(args.server_url, args.token, argv)


def run(server_url, token, command_terms):
    echoes_client = get_echoes_client(server_url, token)
    for echo_message in echoes_client:
        print(echo_message.__dict__)

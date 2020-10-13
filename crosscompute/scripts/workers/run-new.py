from sseclient import SSEClient

from .. import AuthenticatingScript


class RunWorkerScript(AuthenticatingScript):

    def run(self, args, argv):
        super().run(args, argv)
        return run(args.host, args.token, argv)


def run(host, token, command_terms):
    echoes_url = f'{host}/echoes/{token}.json'
    for echo_message in SSEClient(echoes_url):
        print(echo_message.__dict__)

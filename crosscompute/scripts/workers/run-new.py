from invisibleroads.scripts import LoggingScript
from sseclient import SSEClient

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class RunWorkerScript(LoggingScript):

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        return run(host, token, argv)


def run(host, token, command_terms):
    echoes_url = f'{host}/echoes/{token}.json'
    for echo_message in SSEClient(echoes_url):
        print(echo_message.__dict__)

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
        return run(host, token)


def run(host, token):
    headers = {'Authorization': 'Bearer ' + token}
    echoes_url = host + '/echoes.json'
    echoes_client = SSEClient(echoes_url, headers=headers)
    for echo_message in echoes_client:
        print(echo_message)

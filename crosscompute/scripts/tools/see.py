import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class SeeToolScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'tool-id', metavar='TOOL-ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        tool_id = getattr(args, 'tool-id')
        d = run(host, token, tool_id)
        return d


def run(host, token, tool_id=None):
    url = host + '/tools'
    if not tool_id:
        url += '.json'
    else:
        url += f'/{tool_id}.json'
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

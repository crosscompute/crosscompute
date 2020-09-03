import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class SeeResultScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'resultId', metavar='RESULT-ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        result_id = getattr(args, 'resultId')
        d = run(host, token, result_id)
        return d


def run(host, token, result_id=None):
    url = host + '/results'
    if not result_id:
        url += '.json'
    else:
        url += f'/{result_id}.json'
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

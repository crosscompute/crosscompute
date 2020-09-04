import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token,
    get_resource_url)


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
        return run(host, token, result_id)


def run(host, token, result_id=None):
    url = get_resource_url(host, 'results', result_id)
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

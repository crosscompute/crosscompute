import requests
from invisibleroads.scripts import LoggingScript

from ...exceptions import CrossComputeError
from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token,
    load_tool_configuration)


class AddToolScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument('path')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        path = args.path
        is_mock = args.is_mock
        try:
            d = run(host, token, path, is_mock)
        except CrossComputeError as e:
            dictionary = e.args[0]
            exit('\n'.join(f'{k} {v}' for k, v in dictionary.items()))
        return d


def run(host, token, path, is_mock=False):
    url = host + '/tools.json'
    headers = {'Authorization': 'Bearer ' + token}
    dictionary = load_tool_configuration(path)
    if is_mock:
        return dictionary
    response = requests.post(url, headers=headers, json={
        'dictionary': dictionary})
    return response.json()

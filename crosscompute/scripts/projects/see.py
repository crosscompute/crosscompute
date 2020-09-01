import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class SeeProjectScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'projectId', metavar='PROJECT-ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        project_id = getattr(args, 'projectId')
        d = run(host, token, project_id)
        return d


def run(host, token, project_id=None):
    url = host + '/projects'
    if not project_id:
        url += '.json'
    else:
        url += f'/{project_id}.json'
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

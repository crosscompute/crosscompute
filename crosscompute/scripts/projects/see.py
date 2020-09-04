import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token,
    get_resource_url)


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
        return run(host, token, project_id)


def run(host, token, project_id=None):
    url = get_resource_url(host, 'projects', project_id)
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

import json
import requests

from .. import AuthenticatingScript
from ...routines import get_resource_url


class SeeProjectScript(AuthenticatingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'projectId', metavar='PROJECT-ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        d = run(args.server_url, args.token, args.projectId)
        print(json.dumps(d))


def run(server_url, token, project_id=None):
    url = get_resource_url(server_url, 'projects', project_id)
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

import json
import requests

from .. import AuthenticatingScript
from ...routines import get_resource_url


class SeeToolScript(AuthenticatingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            'toolId', metavar='TOOL-ID', nargs='?')

    def run(self, args, argv):
        super().run(args, argv)
        d = run(args.host, args.token, args.toolId)
        print(json.dumps(d))


def run(host, token, tool_id=None):
    url = get_resource_url(host, 'tools', tool_id)
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    return response.json()

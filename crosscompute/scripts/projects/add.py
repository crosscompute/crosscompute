import json
import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class AddProjectScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('--name')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        project_name = args.name
        d = run(host, token, project_name)
        print(json.dumps(d))


def run(host, token, project_name):
    url = host + '/projects.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = {'name': project_name}
    response = requests.post(url, headers=headers, json=d)
    return response.json()

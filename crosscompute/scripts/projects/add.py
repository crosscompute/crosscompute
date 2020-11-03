import json
import requests

from .. import AuthenticatingScript


class AddProjectScript(AuthenticatingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('--name')

    def run(self, args, argv):
        super().run(args, argv)
        d = run(args.server_url, args.token, args.name)
        print(json.dumps(d))


def run(server_url, token, project_name):
    url = server_url + '/projects.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = {'name': project_name}
    response = requests.post(url, headers=headers, json=d)
    return response.json()

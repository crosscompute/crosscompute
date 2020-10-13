import json
import requests

from .. import AuthenticatingScript


class AddResultScript(AuthenticatingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('--name')
        argument_subparser.add_argument('--toolId')
        argument_subparser.add_argument('--toolVersionId')
        argument_subparser.add_argument('--projectId')
        argument_subparser.add_argument('path')

    def run(self, args, argv):
        super().run(args, argv)
        result_name = args.name
        tool_id = args.toolId
        tool_version_id = args.toolVersionId
        project_id = args.projectId
        path = args.path

        if path.endswith('.json'):
            result_dictionary = json.load(open(path, 'rt'))
        else:
            exit()

        if result_name:
            result_dictionary['name'] = result_name
        if tool_id:
            tool = result_dictionary.get('tool', {})
            tool['id'] = tool_id
            result_dictionary['tool'] = tool
        if tool_version_id:
            tool = result_dictionary.get('tool', {})
            tool_version = tool.get('version', {})
            tool_version['id'] = tool_version_id
            tool['version'] = tool_version
            result_dictionary['tool'] = tool
        if project_id:
            project = result_dictionary.get('project', {})
            project['id'] = project_id

        d = run(args.host, args.token, result_dictionary)
        print(json.dumps(d))


def run(host, token, result_dictionary):
    url = host + '/results.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = result_dictionary
    response = requests.post(url, headers=headers, json=d)
    return response.json()

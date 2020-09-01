import json
import requests
from invisibleroads.scripts import LoggingScript

from ...routines import get_crosscompute_host, get_crosscompute_token


class AddResultScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('--name')
        argument_subparser.add_argument('--toolId')
        argument_subparser.add_argument('--toolVersionId')
        argument_subparser.add_argument('--projectId')
        argument_subparser.add_argument('path')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
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
        if tool_version_id:
            tool = result_dictionary.get('tool', {})
            tool_version = tool.get('version', {})
            tool_version['id'] = tool_version_id
        if project_id:
            project = result_dictionary.get('project', {})
            project['id'] = project_id

        return run(host, token, result_dictionary)


def run(host, token, result_dictionary):
    url = host + '/results.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = result_dictionary
    response = requests.post(url, headers=headers, json=d)
    return response.json()

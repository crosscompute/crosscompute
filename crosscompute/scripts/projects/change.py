import json
import requests

from .. import AuthenticatingScript


class ChangeProjectScript(AuthenticatingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('projectId', metavar='PROJECT-ID')
        argument_subparser.add_argument('--name')
        argument_subparser.add_argument('--toolId', action='append')
        argument_subparser.add_argument('--datasetId', action='append')
        argument_subparser.add_argument('--resultId', action='append')

    def run(self, args, argv):
        super().run(args, argv)
        tool_ids = args.toolId or []
        dataset_ids = args.datasetId or []
        result_ids = args.resultId or []
        d = run(
            args.server_url,
            args.token,
            args.projectId,
            args.name,
            tool_ids,
            dataset_ids,
            result_ids)
        print(json.dumps(d))


def run(
    server_url,
    token,
    project_id,
    project_name=None,
    tool_ids=[],
    dataset_ids=[],
    result_ids=[],
):
    url = f'{server_url}/projects/{project_id}.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = {
        'toolIds': tool_ids,
        'datasetIds': dataset_ids,
        'resultIds': result_ids,
    }
    if project_name:
        d['name'] = project_name
    response = requests.patch(url, headers=headers, json=d)
    return response.json()

import requests
from invisibleroads.scripts import LoggingScript

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


class ChangeProjectScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('project-id', metavar='PROJECT-ID')
        argument_subparser.add_argument('--tool-id', action='append')
        argument_subparser.add_argument('--dataset-id', action='append')
        argument_subparser.add_argument('--result-id', action='append')

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        project_id = getattr(args, 'project-id')
        tool_ids = args.tool_id or []
        dataset_ids = args.dataset_id or []
        result_ids = args.result_id or []
        d = run(host, token, project_id, tool_ids, dataset_ids, result_ids)
        return d


def run(host, token, project_id, tool_ids, dataset_ids, result_ids):
    url = f'{host}/projects/{project_id}.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = {
        'toolIds': tool_ids,
        'datasetIds': dataset_ids,
        'resultIds': result_ids,
    }
    response = requests.patch(url, headers=headers, json=d)
    return response.json()

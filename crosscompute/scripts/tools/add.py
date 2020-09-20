# TODO: Consider running worker after add if user asks for it
import json
import requests
from invisibleroads.scripts import LoggingScript

from ...exceptions import CrossComputeError
from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token,
    load_tool_configuration)


MOCK_TEXT = '''
tool name = {tool_name}
tool version = {tool_version_name}
input variable count = {input_variable_count}
output variable count = {output_variable_count}
'''.strip()
REAL_TEXT = MOCK_TEXT + '''

export CROSSCOMPUTE_HOST={host}
export CROSSCOMPUTE_TOKEN={token}
crosscompute workers run {script_command}
'''.rstrip()


class AddToolScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', '-m', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            '--response-format', '-r', choices=['text', 'json'],
            default='text')
        argument_subparser.add_argument('path')

    def run(self, args, argv):
        super().run(args, argv)
        is_mock = args.is_mock
        response_format = args.response_format
        # TODO: Render errors using response_format
        host = get_crosscompute_host()
        token = get_crosscompute_token() if not is_mock else ''
        try:
            d = run(host, token, args.path, is_mock)
        except CrossComputeError as e:
            dictionary = e.args[0]
            # TODO: Render errors in json too if requested
            exit('\n'.join(f'{k} {v}' for k, v in dictionary.items()))
        if response_format == 'json':
            print(json.dumps(d))
        elif is_mock:
            print(MOCK_TEXT.format(
                tool_name=d['name'],
                tool_version_name=d['version']['name'],
                input_variable_count=len(d['input']['variables']),
                output_variable_count=len(d['output']['variables'])))
        else:
            tool_version = d['versions'][0]
            token = tool_version['token']
            script_command = d['script']['command'] if 'script' in d else ''
            print(REAL_TEXT.format(
                # tool_url=d['url'],
                # tool_version_url=tool_version['url'],
                tool_name=d['name'],
                tool_version_name=tool_version['name'],
                input_variable_count=len(tool_version['input'][
                    'variableById']),
                output_variable_count=len(tool_version['output'][
                    'variableById']),
                host=host,
                token=token,
                script_command=script_command))


def run(host, token, path, is_mock=False):
    url = host + '/tools.json'
    headers = {'Authorization': 'Bearer ' + token}
    dictionary = load_tool_configuration(path)
    if is_mock:
        return dictionary
    response = requests.post(url, headers=headers, json={
        'dictionary': dictionary})
    d = response.json()
    if response.status_code != 200:
        raise CrossComputeError(d)
    if 'script' in dictionary:
        d['script'] = dictionary['script']
    return d

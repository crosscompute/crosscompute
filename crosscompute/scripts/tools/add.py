# TODO: Consider running worker after add if user asks for it
import json
import requests
from invisibleroads.scripts import LoggingScript

from ...exceptions import CrossComputeError
from ...routines import (
    get_server_url,
    get_server_token,
    load_tool_definition)


MOCK_TEXT = '''
tool name = {tool_name}
tool version = {tool_version_name}
input variable count = {input_variable_count}
output variable count = {output_variable_count}
'''.strip()
REAL_TEXT = MOCK_TEXT + '''

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
        response_format = args.response_format
        is_response_format_json = response_format == 'json'
        is_mock = args.is_mock
        server_url = get_server_url()
        server_token = get_server_token() if not is_mock else ''
        try:
            d = run(server_url, server_token, args.path, is_mock)
        except CrossComputeError as e:
            dictionary = e.args[0]
            if is_response_format_json:
                message_text = json.dumps(dictionary)
            else:
                message_text = '\n'.join(f'{k} {v}' for k, v in dictionary.items())
            exit(message_text)
        if is_response_format_json:
            print(json.dumps(d))
        elif is_mock:
            print(format_mock_text(d))
        else:
            print(format_real_text(d))


def run(server_url, server_token, path, is_mock=False):
    url = server_url + '/tools.json'
    headers = {'Authorization': 'Bearer ' + server_token}
    dictionary = load_tool_definition(path)
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


def format_mock_text(d):
    return MOCK_TEXT.format(
        tool_name=d['name'],
        tool_version_name=d['version']['name'],
        input_variable_count=len(d['input']['variables']),
        output_variable_count=len(d['output']['variables']))


def format_real_text(d):
    tool_version = d['versions'][0]
    script_command = d['script']['command'] if 'script' in d else ''
    return REAL_TEXT.format(
        # tool_url=d['url'],
        # tool_version_url=tool_version['url'],
        tool_name=d['name'],
        tool_version_name=tool_version['name'],
        input_variable_count=len(tool_version['input'][
            'variableById']),
        output_variable_count=len(tool_version['output'][
            'variableById']),
        token=tool_version['token'],
        script_command=script_command)

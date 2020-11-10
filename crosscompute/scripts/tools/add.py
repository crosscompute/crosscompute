# TODO: Consider running worker after add if user asks for it
import json
import requests
from invisibleroads.scripts import LoggingScript
from sys import exit

from .. import ConnectingScript
from ...exceptions import CrossComputeError
from ...routines import (
    get_server_url,
    get_token,
    load_definition)


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


class AddToolScript(ConnectingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'path', metavar='TOOL_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        as_json = args.as_json
        is_mock = args.is_mock

        run_safely(add_tool, [args.path, is_mock])

        try:
            d = add_tool(args.path, is_mock)
        except CrossComputeError:

        if is_response_format_json:
            print(json.dumps(d))
        elif is_mock:
            print(format_mock_text(d))
        else:
            print(format_real_text(d))


def run(path, is_mock=False):
    dictionary = load_definition(path, kinds=['tool'])
    if is_mock:
        return dictionary
    return fetch_resource('tools', method='POST', data={
        'dictionary': dictionary})


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

# TODO: Periodically check chores even without echo


import json
import pandas
import requests
import subprocess
from collections import defaultdict
from invisibleroads_macros_disk import make_folder
from invisibleroads.scripts import LoggingScript
from os import environ
from os.path import expanduser, join, splitext
from sseclient import SSEClient

from ...routines import (
    get_crosscompute_host,
    get_crosscompute_token)


def save_json(target_path, value_by_id):
    json.dump(value_by_id, open(target_path, 'wt'))


def load_json(source_path):
    return json.load(open(source_path, 'rt'))


def load_csv(source_path):
    return pandas.read_csv(source_path)


SAVE_BY_EXTENSION = {
    '.json': save_json,
}
LOAD_BY_EXTENSION = {
    '.json': load_json,
    '.csv': load_csv,
}


class RunWorkerScript(LoggingScript):

    '''
    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        # argument_subparser.add_argument(
            # 'script-arguments', nargs=argparse.REMAINDER)
    '''

    def run(self, args, argv):
        super().run(args, argv)
        host = get_crosscompute_host()
        token = get_crosscompute_token()
        return run(host, token, argv)


def run(host, token, script_arguments):
    headers = {'Authorization': 'Bearer ' + token}
    echoes_url = host + '/echoes.json'
    chores_url = host + '/chores.json'
    for echo_message in SSEClient(echoes_url, headers=headers):
        print(echo_message.__dict__)
        if echo_message.event == 'i':
            # TODO: Handle invalid json
            d = json.loads(echo_message.data)
            if d.get('%') == 100:
                print(d.get('#'), 'done')
                continue

            root_folder = expanduser('~/.crosscompute')
            results_folder = join(root_folder, 'results')

            while True:
                response = requests.get(chores_url, headers=headers)
                print(response.__dict__)
                chore_dictionary = response.json()
                if not chore_dictionary:
                    break
                # print(chore_dictionary)
                # TODO: Assert result in chore_dictionary
                try:
                    tool_dictionary = chore_dictionary['tool']
                    result_dictionary = chore_dictionary['result']
                except KeyError as e:
                    print('missing', e)
                    continue
                tool_version_dictionary = tool_dictionary['versions'][0]
                tool_input_dictionary = tool_version_dictionary['input']
                tool_input_variable_by_id = tool_input_dictionary['variableById']
                tool_output_dictionary = tool_version_dictionary['output']
                tool_output_variable_by_id = tool_output_dictionary['variableById']
                result_id = result_dictionary['id']
                result_token = result_dictionary['token']
                result_input_variable_data_by_id = result_dictionary[
                    'inputVariableDataById']
                result_folder = join(results_folder, result_id)
                input_folder = make_folder(join(result_folder, 'input'))
                output_folder = make_folder(join(result_folder, 'output'))

                # TODO: Get tool from cloud

                '''
                for (
                    variable_id,
                    variable_data,
                ) in result_input_variable_data_by_id.items():
                    variable = tool_input_variable_by_id[variable_id]
                    variable_view = variable['view']
                    variable_path = variable['path']
                '''

                value_by_id_by_path = defaultdict(dict)
                for (
                    variable_id,
                    variable_definition,
                ) in tool_input_variable_by_id.items():
                    # variable_id = variable_definition['id']
                    variable_path = variable_definition['path']
                    variable_value = result_input_variable_data_by_id[
                        variable_id]['value']
                    variable_view = variable_definition['view']
                    file_extension = splitext(variable_path)[1]

                    # TODO: This needs to be rewritten
                    if variable_view in (
                        'number',
                        'text',
                    ) and file_extension in (
                        '.csv',
                        '.json',
                    ):
                        value_by_id = value_by_id_by_path[variable_path]
                        value_by_id[variable_id] = variable_value
                        continue
                    # TODO: This needs to be specific to the view
                    p = join(input_folder, variable_path)
                    # print(p)
                    open(p, 'wt').write(variable_value)
                    # print(variable_path, variable_value)
                value_by_id_by_path = dict(value_by_id_by_path)

                for (
                    variable_path, value_by_id,
                ) in value_by_id_by_path.items():
                    file_extension = splitext(variable_path)[1]
                    file_path = join(input_folder, variable_path)
                    save = SAVE_BY_EXTENSION[file_extension]
                    save(file_path, value_by_id)

                script_folder = '.'
                # TODO: Select environment variables to expose
                subprocess.run(script_arguments, env=dict(environ, **{
                    'CROSSCOMPUTE_INPUT_FOLDER': input_folder,
                    'CROSSCOMPUTE_OUTPUT_FOLDER': output_folder,
                }), cwd=script_folder)

                output_variable_data_by_id = {}
                for (
                    variable_id,
                    variable_dictionary,
                ) in tool_output_variable_by_id.items():
                    # variable_id = variable_dictionary['id']
                    variable_view = variable_dictionary['view']
                    variable_path = variable_dictionary['path']
                    file_extension = splitext(variable_path)[1]
                    file_path = join(output_folder, variable_path)

                    if variable_view in (
                        'number',
                        'text',
                    ) and file_extension in (
                        '.csv',
                        '.json',
                    ):
                        load = LOAD_BY_EXTENSION[file_extension]
                        value_by_id = load(file_path)
                        variable_value = value_by_id[variable_id]
                        output_variable_data_by_id[variable_id] = {
                            'value': variable_value}
                        continue

                    if variable_view in (
                        'table',
                    ) and file_extension in (
                        '.csv',
                    ):
                        load = LOAD_BY_EXTENSION[file_extension]
                        table = load(file_path)
                        columns = table.columns.to_list()
                        rows = list(table.to_dict('split')['data'])
                        table_value = {'rows': rows, 'columns': columns}
                        # print(table_value)
                        output_variable_data_by_id[variable_id] = {
                            'value': table_value}

                result_url = host + '/results/' + result_id + '.json'
                response = requests.patch(result_url, headers={
                    'Authorization': 'Bearer ' + result_token,
                }, json={
                    'progress': 100,
                    'outputVariableDataById': output_variable_data_by_id,
                })
                # print(response.__dict__)

                # TODO: Put result in cloud

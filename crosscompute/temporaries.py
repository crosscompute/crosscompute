import base64
import json
import pandas
import requests
import shlex
import strictyaml
import subprocess
from collections import defaultdict
from copy import deepcopy
from crosscompute import __version__
from crosscompute.exceptions import (
    CrossComputeDefinitionError, CrossComputeExecutionError, CrossComputeError)
from crosscompute.routines import get_crosscompute_host, normalize_tool_definition
from invisibleroads_macros_disk import make_folder, make_random_folder
from itertools import product
from os import environ
from os.path import abspath, dirname, exists, expanduser, join, splitext
from subprocess import CalledProcessError
from tinycss2 import parse_stylesheet

# TODO: Check that file extension is supported for each variable type


S = {
    'folder': expanduser('~/.crosscompute'),
    'draft.id.length': 16,
}


def run(context_path):
    # Load automation
    context_folder = dirname(context_path)

    try:
        automation_path = find_parent_path(context_folder, 'automation.yml')
    except OSError:
        raise CrossComputeError({'automation': 'missing'})

    automation_definition = load_definition(automation_path, kinds=['automation'])
    assert automation_definition['kind'] == 'result'
    result_definition = automation_definition

    # Run tool
    # Render documents
    document_dictionaries = []
    for result_dictionary in yield_result_dictionary(result_definition):
        tool_definition = result_dictionary.pop('tool')
        result_dictionary = run_tool(tool_definition, result_dictionary)
        print(result_dictionary['outputVariableDataById'])
        document_dictionary = render_result(tool_definition, result_dictionary)
        document_dictionaries.append(document_dictionary)
    print(document_dictionaries)

    # Post documents
    host = get_crosscompute_host()
    token = ''
    url = host + '/prints.json'
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.post(url, headers=headers, json={
        'documents': document_dictionaries})
    # !!!
    if response.status_code != 200:
        print(response.content)
    response_json = response.json()
    # print_id = response_json['id']
    file_url = response_json['url']
    # Move draft into local prints
    return file_url


def find_parent_path(folder, name):
    this_folder = abspath(folder)
    while True:
        this_path = join(this_folder, name)
        if exists(this_path):
            break
        parent_folder = dirname(this_folder)
        if parent_folder == this_folder:
            raise OSError
        this_folder = parent_folder
    return this_path


def load_definition(path, kinds=None):
    raw_definition = load_raw_definition(path)
    folder = dirname(path)
    definition = normalize_definition(raw_definition, folder, kinds)
    definition['folder'] = folder
    return definition


def load_raw_definition(path):
    try:
        text = open(path, 'rt').read()
    except OSError:
        raise CrossComputeDefinitionError({'path': 'bad'})
    raw_definition = strictyaml.load(text).data
    if not isinstance(raw_definition, dict):
        raise CrossComputeDefinitionError({'definition': 'expected dictionary'})
    try:
        protocol_name = raw_definition.pop('crosscompute')
    except KeyError:
        raise CrossComputeDefinitionError({'crosscompute': 'required'})
    if protocol_name != __version__:
        raise CrossComputeDefinitionError({'crosscompute': 'expected ' + __version__})
    return dict(raw_definition)


def normalize_definition(raw_definition, folder, kinds=None):
    try:
        kind = raw_definition['kind'].lower()
    except KeyError:
        raise CrossComputeDefinitionError({'kind': 'required'})
    if kinds and kind not in kinds:
        raise CrossComputeDefinitionError({'kind': 'expected ' + ' or '.join(kinds)})
    if kind == 'automation':
        definition = normalize_automation_definition(raw_definition, folder)
    elif kind == 'result':
        definition = normalize_result_definition(raw_definition, folder)
    elif kind == 'tool':
        definition = normalize_tool_definition(raw_definition, folder)
    else:
        definition = raw_definition
    return definition


def normalize_automation_definition(raw_automation_definition, folder):
    try:
        path = join(folder, raw_automation_definition['path'])
    except KeyError as e:
        raise CrossComputeDefinitionError({e.args[0]: 'required'})
    return load_definition(path, kinds=['result', 'report'])


def normalize_result_definition(raw_result_definition, folder):
    if 'path' in raw_result_definition:
        result_definition_path = join(folder, raw_result_definition['path'])
        result_definition = load_definition(result_definition_path, kinds=['result'])
    else:
        result_definition = {}
    tool_definition = dict(raw_result_definition.get(
        'tool', result_definition.get('tool', {})))
    if 'path' in tool_definition:
        tool_definition_path = join(folder, tool_definition['path'])
        tool_definition = load_definition(tool_definition_path)
    input_variable_data_by_id = {k: dict(v) for k, v in {
        **result_definition.get('inputVariableDataById', {}),
        **raw_result_definition.get('inputVariableDataById', {})}.items()}

    try:
        input_variable_definitions = tool_definition['input']['variables']
    except KeyError:
        pass
    else:
        for variable_definition in input_variable_definitions:
            variable_id = variable_definition['id']
            variable_view = variable_definition['view']
            try:
                variable_data = input_variable_data_by_id[variable_id]
            except KeyError:
                continue
            if variable_view == 'number':
                if 'values' in variable_data:
                    variable_data['values'] = [parse_number(_) for _ in variable_data['values']]
                elif 'value' in variable_data:
                    variable_data['value'] = parse_number(variable_data['value'])

    style_definition = dict(raw_result_definition.get(
        'style', result_definition.get('style')))
    if 'path' in style_definition:
        style_path = join(folder, style_definition['path'])
        style_definition = {'rules': load_style_rule_strings(style_path)}

    result_definition['tool'] = tool_definition
    result_definition['inputVariableDataById'] = input_variable_data_by_id
    result_definition['style'] = style_definition
    result_definition['format'] = raw_result_definition.get(
        'format', result_definition.get('format'))
    result_definition['kind'] = 'result'
    return result_definition


def parse_number(raw_value):
    try:
        value = int(raw_value)
    except ValueError:
        value = float(raw_value)
    return value


def load_style_rule_strings(style_path):
    try:
        style_text = open(style_path, 'rt').read()
    except OSError:
        raise CrossComputeDefinitionError({'path': 'bad ' + style_path})
    return normalize_style_rule_strings([style_text])


def normalize_style_rule_strings(raw_style_rule_strings):
    try:
        style_text = '\n'.join(raw_style_rule_strings)
        style_rules = parse_stylesheet(
            style_text, skip_comments=True, skip_whitespace=True)
        style_rule_strings = [_.serialize() for _ in style_rules]
    except TypeError:
        raise CrossComputeDefinitionError({'styles': 'bad'})
    return style_rule_strings


def yield_result_dictionary(result_definition):
    special_variable_ids = []
    special_values_list = []
    input_variable_data_by_id = result_definition['inputVariableDataById']
    for variable_id, variable_data in input_variable_data_by_id.items():
        if 'values' not in variable_data:
            continue
        special_variable_ids.append(variable_id)
        special_values_list.append(variable_data['values'])
    for values in product(*special_values_list):
        special_variable_data_by_id = {
            k: {'value': v} for k, v in zip(special_variable_ids, values)}
        d = dict(result_definition)
        d['inputVariableDataById'] = {
            **input_variable_data_by_id,
            **special_variable_data_by_id}
        yield d


def run_tool(tool_definition, result_dictionary):
    script_command = tool_definition['script']['command']
    script_folder = tool_definition['folder']
    result_folder = get_result_folder(result_dictionary)
    folder_by_name = {k: make_folder(join(result_folder, k)) for k in [
        'input', 'output', 'log', 'debug']}
    prepare_input_folder(
        folder_by_name['input'],
        tool_definition['input']['variables'],
        result_dictionary['inputVariableDataById'])
    run_script(
        script_command,
        script_folder,
        folder_by_name['input'],
        folder_by_name['output'],
        folder_by_name['log'],
        folder_by_name['debug'])
    for folder_name in 'output', 'log', 'debug':
        if folder_name not in tool_definition:
            continue
        result_dictionary[folder_name + 'VariableDataById'] = process_output_folder(
            folder_by_name[folder_name], tool_definition[folder_name]['variables'])
    return result_dictionary


def get_result_folder(result_dictionary):
    folder = S['folder']
    if 'id' in result_dictionary:
        result_id = result_dictionary['id']
        result_folder = join(folder, 'results', result_id)
    else:
        drafts_folder = join(folder, 'drafts')
        result_folder = make_random_folder(drafts_folder, S['draft.id.length'])
    return result_folder


def render_result(tool_definition, result_dictionary):
    blocks = render_blocks(tool_definition, result_dictionary)
    styles = result_dictionary.get('style', {}).get('rules', [])
    document_dictionary = {
        'blocks': blocks,
        'styles': styles,
    }
    return document_dictionary


def prepare_input_folder(input_folder, variable_definitions, variable_data_by_id):
    value_by_id_by_path = defaultdict(dict)

    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        variable_path = variable_definition['path']
        variable_view = variable_definition['view']
        raw_value = variable_data_by_id[variable_id]['value']
        if variable_view == 'number':
            variable_value = parse_number(raw_value)
        elif variable_view == 'text':
            variable_value = raw_value
        value_by_id_by_path[variable_path][variable_id] = variable_value

    for variable_path, value_by_id in value_by_id_by_path.items():
        file_extension = splitext(variable_path)[1]
        file_path = join(input_folder, variable_path)
        save = SAVE_BY_EXTENSION[file_extension]
        save(file_path, value_by_id)


def run_script(script_command, script_folder, input_folder, output_folder, log_folder, debug_folder):
    script_arguments = shlex.split(script_command)
    stdout_file = open(join(debug_folder, 'stdout.log'), 'wt')
    stderr_file = open(join(debug_folder, 'stderr.log'), 'wt')
    subprocess_options = {
        'cwd': script_folder,
        'stdout': stdout_file,
        'stderr': stderr_file,
        'encoding': 'utf-8',
        'check': True,
    }
    try:
        subprocess.run(script_arguments, env={
            'PATH': environ.get('PATH', ''),
            'VIRTUAL_ENV': environ.get('VIRTUAL_ENV', ''),
            'CROSSCOMPUTE_INPUT_FOLDER': input_folder,
            'CROSSCOMPUTE_OUTPUT_FOLDER': output_folder,
            'CROSSCOMPUTE_LOG_FOLDER': log_folder,
            'CROSSCOMPUTE_DEBUG_FOLDER': debug_folder,
        }, **subprocess_options)
    except FileNotFoundError as e:
        raise CrossComputeDefinitionError(e)
    except CalledProcessError as e:
        raise CrossComputeExecutionError(e)
    stdout_file.close()
    stderr_file.close()


def process_output_folder(output_folder, variable_definitions):
    variable_data_by_id = {}

    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        variable_path = variable_definition['path']
        variable_view = variable_definition['view']
        file_extension = splitext(variable_path)[1]
        file_path = join(output_folder, variable_path)

        if variable_view == 'number':
            # TODO: Handle case when extension is unsupported
            load = LOAD_BY_EXTENSION[file_extension]
            value_by_id = load(file_path)
            # TODO: Handle case when variable id is not found
            variable_value = value_by_id[variable_id]
        if variable_view == 'table':
            # TODO: Handle case when extension is unsupported
            load = LOAD_BY_EXTENSION[file_extension]
            table = load(file_path)
            columns = table.columns.to_list()
            rows = list(table.to_dict('split')['data'])
            variable_value = {'rows': rows, 'columns': columns}
        elif variable_view == 'image':
            with open(file_path, 'rb') as image_file:
                variable_value = base64.b64encode(image_file.read())
            variable_value = variable_value.decode('utf-8')
        variable_data_by_id[variable_id] = {'value': variable_value}
    return variable_data_by_id


def render_blocks(tool_definition, result_dictionary):
    input_variable_definition_by_id = {_['id']: _ for _ in tool_definition[
        'input']['variables']}
    output_variable_definition_by_id = {_['id']: _ for _ in tool_definition[
        'output']['variables']}
    input_variable_data_by_id = result_dictionary['inputVariableDataById']
    output_variable_data_by_id = result_dictionary['outputVariableDataById']
    template_dictionary = get_template_dictionary(
        tool_definition, result_dictionary)
    blocks = deepcopy(template_dictionary['blocks'])
    for block in blocks:
        if 'id' not in block:
            continue
        variable_id = block['id']
        if variable_id in output_variable_definition_by_id:
            variable_definition = output_variable_definition_by_id[variable_id]
            variable_data = output_variable_data_by_id.get(variable_id, {})
        elif variable_id in input_variable_definition_by_id:
            variable_definition = input_variable_definition_by_id[variable_id]
            variable_data = input_variable_data_by_id.get(variable_id, {})
        else:
            continue
        block['name'] = variable_definition['name']
        block['view'] = variable_definition['view']
        block['data'] = variable_data
    return blocks


def get_template_dictionary(tool_definition, result_dictionary):
    template_dictionaries = tool_definition['output'].get('templates', [])
    if not template_dictionaries:
        variable_definitions = tool_definition['output'].get('variables', [])
        return make_template_dictionary(variable_definitions)
    template_id = result_dictionary.get('template', {}).get(
        'id', '').casefold()
    for template_dictionary in template_dictionaries:
        if template_dictionary.get('id', '').casefold() == template_id:
            break
    else:
        template_dictionary = template_dictionaries[0]
    return template_dictionary


def make_template_dictionary(variable_definitions):
    return {
        'id': 'generated',
        'name': 'Generated',
        'blocks': [{'id': _['id']} for _ in variable_definitions],
    }


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

# TODO: Check that file extension is supported for each variable type
import base64
import csv
import geojson
import json
import re
import requests
import shlex
import strictyaml
import subprocess
from collections import defaultdict
from copy import deepcopy
from invisibleroads_macros_disk import make_folder, make_random_folder
from itertools import product
from os import environ
from os.path import abspath, dirname, exists, isdir, join, splitext
from pyramid.httpexceptions import HTTPInternalServerError
from sseclient import SSEClient
from subprocess import CalledProcessError
from sys import exc_info
from tinycss2 import parse_stylesheet
from traceback import print_exception

from . import __version__
from .constants import (
    AUTOMATION_FILE_NAME,
    CLIENT_URL,
    DEFAULT_VIEW_NAME,
    L,
    S,
    SERVER_URL,
    VIEW_NAMES)
from .exceptions import (
    CrossComputeDefinitionError,
    CrossComputeError,
    CrossComputeExecutionError)
from .macros import get_environment_value, parse_number


VARIABLE_TEXT_PATTERN = re.compile(r'({[^}]+})')
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')


def get_client_url():
    return get_environment_value('CROSSCOMPUTE_CLIENT', CLIENT_URL)


def get_server_url():
    return get_environment_value('CROSSCOMPUTE_SERVER', SERVER_URL)


def get_token():
    return get_environment_value('CROSSCOMPUTE_TOKEN', is_required=True)


def get_resource_url(server_url, resource_name, resource_id=None):
    url = server_url + '/' + resource_name
    if resource_id:
        url += '/' + resource_id
    return url + '.json'


def get_echoes_client(server_url, token):
    url = f'{server_url}/echoes/{token}.json'
    return SSEClient(url)


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
        raise CrossComputeDefinitionError({'path': 'is bad'})
    raw_definition = strictyaml.load(text).data
    if not isinstance(raw_definition, dict):
        raise CrossComputeDefinitionError({'definition': 'must be a dictionary'})
    try:
        protocol_name = raw_definition.pop('crosscompute')
    except KeyError:
        raise CrossComputeDefinitionError({'crosscompute': 'is required'})
    if protocol_name != __version__:
        raise CrossComputeDefinitionError({'crosscompute': 'should be ' + __version__})
    return dict(raw_definition)


def load_style_rule_strings(style_path):
    try:
        style_text = open(style_path, 'rt').read()
    except OSError:
        raise CrossComputeDefinitionError({'path': 'is bad ' + style_path})
    return normalize_style_rule_strings([style_text])


def normalize_definition(raw_definition, folder, kinds=None):
    try:
        kind = raw_definition['kind'].lower()
    except KeyError:
        raise CrossComputeDefinitionError({'kind': 'is required'})
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


def normalize_tool_definition(dictionary, folder):
    try:
        assert dictionary['kind'].lower() == 'tool'
    except (KeyError, AssertionError):
        raise CrossComputeDefinitionError({'kind': 'must be tool'})
    d = {}
    if 'id' in dictionary:
        d['id'] = dictionary['id']
    if 'slug' in dictionary:
        d['slug'] = dictionary['slug']
    try:
        d['name'] = dictionary['name']
        d['version'] = normalize_version_dictionary(dictionary['version'])
    except KeyError as e:
        raise CrossComputeDefinitionError({e.args[0]: 'is required'})
    d['input'] = normalize_put_definition('input', dictionary, folder)
    d['output'] = normalize_put_definition('output', dictionary, folder)
    if 'tests' in dictionary:
        d['tests'] = normalize_tests_definition('tests', dictionary)
    if 'script' in dictionary:
        d['script'] = normalize_script_definition('script', dictionary)
    if 'environment' in dictionary:
        d['environment'] = normalize_environment_definition(
            'environment', dictionary)
    return d


def normalize_put_definition(key, dictionary, folder=None):
    d = {}

    try:
        put_dictionary = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} definition')
        return d

    try:
        variable_dictionaries = put_dictionary['variables']
    except KeyError:
        L.warning(f'missing {key} variables definition')
        variable_dictionaries = []
    else:
        variable_dictionaries = normalize_variable_dictionaries(
            variable_dictionaries)
        d['variables'] = variable_dictionaries

    try:
        template_dictionaries = put_dictionary['templates']
    except KeyError:
        L.warning(f'missing {key} templates definition')
        template_dictionaries = []
    else:
        template_dictionaries = normalize_template_dictionaries(
            template_dictionaries, variable_dictionaries, folder)
        d['templates'] = template_dictionaries

    return d


def normalize_tests_definition(key, dictionary):
    try:
        raw_test_dictionaries = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} definition')
        raw_test_dictionaries = []
    return normalize_test_dictionaries(raw_test_dictionaries)


def normalize_script_definition(key, dictionary):
    try:
        raw_script_dictionary = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} definition')
        raw_script_dictionary = {}
    return normalize_script_dictionary(raw_script_dictionary)


def normalize_environment_definition(key, dictionary):
    try:
        raw_environment_dictionary = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} definition')
        raw_environment_dictionary = {}
    return normalize_environment_dictionary(raw_environment_dictionary)


def normalize_blocks_definition(key, dictionary, folder=None):
    if 'blocks' in dictionary:
        block_dictionaries = dictionary['blocks']
    elif 'path' in dictionary and folder is not None:
        template_path = join(folder, dictionary['path'])
        block_dictionaries = load_block_dictionaries(template_path)
    else:
        block_dictionaries = []
    return normalize_block_dictionaries(block_dictionaries)


def normalize_variable_dictionaries(raw_variable_dictionaries):
    variable_dictionaries = []
    for raw_variable_dictionary in raw_variable_dictionaries:
        try:
            variable_id = raw_variable_dictionary['id']
            variable_path = raw_variable_dictionary['path']
        except KeyError as e:
            raise CrossComputeDefinitionError({
                e.args[0]: 'is required for each variable'})
        variable_dictionary = {
            'id': variable_id,
            'name': raw_variable_dictionary.get(
                'name', variable_id),
            'view': raw_variable_dictionary.get(
                'view', DEFAULT_VIEW_NAME),
            'path': variable_path,
        }
        variable_dictionaries.append(variable_dictionary)
    return variable_dictionaries


def normalize_template_dictionaries(
        raw_template_dictionaries, variable_dictionaries, folder=None):
    template_dictionaries = []
    for raw_template_dictionary in raw_template_dictionaries:
        try:
            template_id = raw_template_dictionary['id']
            template_name = raw_template_dictionary['name']
        except KeyError as e:
            raise CrossComputeDefinitionError({
                e.args[0]: 'is required for each template'})
        template_blocks = normalize_blocks_definition(
            'blocks', raw_template_dictionary, folder)
        if not template_blocks:
            continue
        template_dictionaries.append({
            'id': template_id,
            'name': template_name,
            'blocks': template_blocks,
        })
    if not template_dictionaries:
        template_dictionaries.append({
            'id': 'generated',
            'name': 'Generated',
            'blocks': [{'id': _['id']} for _ in variable_dictionaries],
        })
    return template_dictionaries


def normalize_test_dictionaries(raw_test_dictionaries):
    return [{
        'id': _['id'],
        'name': _['name'],
        'path': _['path'],
    } for _ in raw_test_dictionaries]


def normalize_block_dictionaries(raw_block_dictionaries):
    if not isinstance(raw_block_dictionaries, list):
        raise CrossComputeDefinitionError({
            'blocks': 'must be a list'})
    block_dictionaries = []
    for raw_block_dictionary in raw_block_dictionaries:
        has_id = 'id' in raw_block_dictionary
        has_view = 'view' in raw_block_dictionary
        has_data = 'data' in raw_block_dictionary
        block_dictionary = {}
        if has_id:
            block_dictionary['id'] = raw_block_dictionary['id']
        if has_view:
            raw_view_name = raw_block_dictionary['view']
            view_name = normalize_view_name(raw_view_name)
            block_dictionary['view'] = view_name
        elif not has_id:
            raise CrossComputeDefinitionError({
                'view': 'is required if block lacks id'})
        if has_data:
            raw_data_dictionary = raw_block_dictionary['data']
            data_dictionary = normalize_data_dictionary(
                raw_data_dictionary, view_name)
            block_dictionary['data'] = data_dictionary
        '''
        elif not has_data:
            raise CrossComputeDefinitionError({
                'data': 'is required if block lacks id'})
        '''
        # TODO: Consider when to enforce data ==> maybe flag
        block_dictionaries.append(block_dictionary)
    return block_dictionaries


def normalize_version_dictionary(raw_version_dictionary):
    if not isinstance(raw_version_dictionary, dict):
        raise CrossComputeDefinitionError({
            'version': 'must be a dictionary'})

    has_id = 'id' in raw_version_dictionary
    has_name = 'name' in raw_version_dictionary
    if not has_id and not has_name:
        raise CrossComputeDefinitionError({
            'version': 'must be id or name'})

    version_dictionary = {}
    if has_id:
        version_dictionary['id'] = raw_version_dictionary['id']
    elif has_name:
        version_dictionary['name'] = raw_version_dictionary['name']
    return version_dictionary


def normalize_data_dictionary(raw_data_dictionary, view_name):
    if not isinstance(raw_data_dictionary, dict):
        raise CrossComputeDefinitionError({
            'data': 'must be a dictionary'})

    has_values = 'values' in raw_data_dictionary
    has_value = 'value' in raw_data_dictionary
    has_file = 'file' in raw_data_dictionary
    if not has_values and not has_value and not has_file:
        raise CrossComputeDefinitionError({
            'data': 'must be values or value or file'})

    data_dictionary = {}
    if has_values:
        data_dictionary['values'] = normalize_values(
            raw_data_dictionary['values'])
    elif has_value:
        data_dictionary['value'] = normalize_value_dictionary(
            raw_data_dictionary['value'], view_name)
    elif has_file:
        data_dictionary['file'] = normalize_file_dictionary(
            raw_data_dictionary['file'])
    return data_dictionary


def normalize_script_dictionary(raw_script_dictionary):
    uri = raw_script_dictionary['uri']
    folder = raw_script_dictionary['folder']
    command = raw_script_dictionary['command']
    return {
        'uri': uri,
        'folder': folder,
        'command': command,
    }


def normalize_environment_dictionary(raw_environment_dictionary):
    image = raw_environment_dictionary['image']
    processor = raw_environment_dictionary['processor']
    memory = raw_environment_dictionary['memory']
    return {
        'image': image,
        'processor': processor,
        'memory': memory,
    }


def normalize_values(raw_values):
    try:
        values = list(raw_values)
    except TypeError:
        raise CrossComputeDefinitionError({'values': 'must be a list'})
    return values


def normalize_value_dictionary(raw_value_dictionary, view_name=None):
    # TODO
    return raw_value_dictionary


def normalize_file_dictionary(raw_file_dictionary):
    # TODO
    return raw_file_dictionary


def normalize_view_name(raw_view_name):
    if not isinstance(raw_view_name, str):
        raise CrossComputeDefinitionError({'view': 'must be a string'})

    view_name = raw_view_name.lower()
    if view_name not in VIEW_NAMES:
        raise CrossComputeDefinitionError({'view': 'must be ' + ' or '.join(VIEW_NAMES)})
    return view_name


def normalize_style_rule_strings(raw_style_rule_strings):
    if not isinstance(raw_style_rule_strings, list):
        raise CrossComputeDefinitionError({
            'styles': 'must be a list'})
    try:
        style_text = '\n'.join(raw_style_rule_strings)
        style_rules = parse_stylesheet(
            style_text, skip_comments=True, skip_whitespace=True)
        style_rule_strings = [_.serialize() for _ in style_rules]
    except TypeError:
        raise CrossComputeDefinitionError({'styles': 'is bad'})
    return style_rule_strings


def load_block_dictionaries(template_path):
    try:
        template_text = open(template_path, 'rt').read()
    except IOError:
        raise CrossComputeDefinitionError({
            'path': f'is bad for {template_path}'})
    return parse_block_dictionaries(template_text)


def parse_block_dictionaries(template_text):
    block_dictionaries = []
    for text in VARIABLE_TEXT_PATTERN.split(template_text):
        text = text.strip()
        if not text:
            continue
        match = VARIABLE_ID_PATTERN.match(text)
        if match:
            variable_id = match.group(1)
            block_dictionaries.append({
                'id': variable_id,
            })
        else:
            block_dictionaries.append({
                'view': 'markdown',
                'data': {
                    'value': text,
                },
            })
    return block_dictionaries


def find_relevant_path(path, name=''):
    if not exists(path):
        raise OSError({'path': 'is bad'})
    path = abspath(path)

    if isdir(path):
        folder = path
    else:
        base, extension = splitext(path)
        expected_extension = splitext(name)[1]
        if extension == expected_extension:
            return path
        modified_path = base + expected_extension
        if exists(modified_path):
            return modified_path
        folder = dirname(path)

    this_folder = folder
    while True:
        this_path = join(this_folder, name)
        if exists(this_path):
            break
        parent_folder = dirname(this_folder)
        if parent_folder == this_folder:
            raise OSError({'path': 'is missing'})
        this_folder = parent_folder
    return this_path


def run_automation(path):
    try:
        automation_path = find_relevant_path(
            path, AUTOMATION_FILE_NAME)
    except OSError:
        raise CrossComputeExecutionError({'automation': 'is missing'})
    L.info(f'Loading {automation_path}...')
    automation_definition = load_definition(automation_path, kinds=['automation'])
    automation_kind = automation_definition['kind']
    if automation_kind == 'result':
        d = run_result_automation(automation_definition)
    elif automation_kind == 'report':
        d = {}
    return d


def run_result_automation(result_definition):
    document_dictionaries = []
    for result_dictionary in yield_result_dictionary(result_definition):
        tool_definition = result_dictionary.pop('tool')
        result_dictionary = run_tool(tool_definition, result_dictionary)
        document_dictionary = render_result(tool_definition, result_dictionary)
        document_dictionaries.append(document_dictionary)
    # TODO: Enable offline mode
    server_url = get_server_url()
    token = get_token()
    url = server_url + '/prints.json'
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.post(url, headers=headers, json={
        'documents': document_dictionaries})
    if response.status_code != 200:
        print(response.content)
        raise HTTPInternalServerError({})
    response_json = response.json()
    return {
        'url': response_json['url']
    }


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


def process_output_folder(output_folder, variable_definitions):
    variable_data_by_id = {}
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        variable_path = variable_definition['path']
        variable_view = variable_definition['view']
        file_extension = splitext(variable_path)[1]
        file_path = join(output_folder, variable_path)
        try:
            load_by_extension = LOAD_BY_EXTENSION_BY_VIEW[variable_view]
        except KeyError:
            raise HTTPInternalServerError({
                'view': 'is not yet implemented for ' + variable_view})
        try:
            load = load_by_extension[file_extension]
        except KeyError:
            raise CrossComputeDefinitionError({
                'path': 'has unsupported extension ' + file_extension})
        try:
            variable_value = load(file_path, variable_id)
        except OSError:
            raise CrossComputeDefinitionError({
                'path': 'is bad ' + file_path})
        except UnicodeDecodeError:
            raise CrossComputeExecutionError({
                'path': f'is not {variable_view} ' + file_path})
        except CrossComputeError:
            raise
        except Exception:
            print_exception(*exc_info())
            raise HTTPInternalServerError({
                'path': 'triggered an unexpected exception'})
        variable_data_by_id[variable_id] = {'value': variable_value}
    return variable_data_by_id


def make_template_dictionary(variable_definitions):
    return {
        'id': 'generated',
        'name': 'Generated',
        'blocks': [{'id': _['id']} for _ in variable_definitions],
    }


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


def save_json(target_path, value_by_id):
    json.dump(value_by_id, open(target_path, 'wt'))


def load_value_json(source_path, variable_id):
    d = json.load(open(source_path, 'rt'))
    try:
        variable_value = d[variable_id]
    except KeyError:
        raise CrossComputeExecutionError({
            'variable': f'could not find {variable_id} in {source_path}'})
    return variable_value


def load_text_json(source_path, variable_id):
    variable_value = load_value_json(source_path, variable_id)
    return {'value': variable_value}


def load_text_txt(source_path, variable_id):
    variable_value = open(source_path, 'rt').read()
    return {'value': variable_value}


def load_number_json(source_path, variable_id):
    variable_value = load_value_json(source_path, variable_id)
    try:
        variable_value = parse_number(variable_value)
    except ValueError:
        raise CrossComputeExecutionError({
            'variable': f'could not parse {variable_id} as a number'})
    return {'value': variable_value}


def load_markdown_md(source_path, variable_id):
    return load_text_txt(source_path, variable_id)


def load_table_csv(source_path, variable_id):
    csv_reader = csv.reader(open(source_path, 'rt'))
    columns = next(csv_reader)
    rows = list(csv_reader)
    variable_value = {'columns': columns, 'rows': rows}
    return {'value': variable_value}


def load_image_png(source_path, variable_id):
    with open(source_path, 'rb') as source_file:
        variable_value = base64.b64encode(source_file.read())
    variable_value = variable_value.decode('utf-8')
    return {'value': variable_value}


def load_map_geojson(source_path, variable_id):
    variable_value = geojson.load(open(source_path, 'rt'))
    return {'value': variable_value}


LOAD_BY_EXTENSION_BY_VIEW = {
    'text': {
        '.json': load_text_json,
        '.txt': load_text_txt,
    },
    'number': {
        '.json': load_number_json,
    },
    'markdown': {
        '.md': load_markdown_md,
    },
    'table': {
        '.csv': load_table_csv,
    },
    'image': {
        '.png': load_image_png,
    },
    'map': {
        '.geojson': load_map_geojson,
    },
}


def load_text_data(source_path, variable_id):
    pass


def load_number_data(source_path, variable_id):
    pass


def load_markdown_data(source_path, variable_id):
    pass


def load_table_data(source_path, variable_id):
    pass


def load_image_data(source_path, variable_id):
    pass


def load_map_data(source_path, variable_id):
    pass


LOAD_DATA_BY_VIEW_NAME = {
    'text': load_text_data,
    'number': load_number_data,
    'markdown': load_markdown_data,
    'table': load_table_data,
    'image': load_image_data,
    'map': load_map_data,
}

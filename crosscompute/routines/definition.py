import json
import re
import strictyaml
from invisibleroads_macros_text import normalize_key
from os.path import dirname, join
from tinycss2 import parse_stylesheet

from .connection import fetch_resource
from .. import __version__
from ..constants import (
    DEFAULT_VIEW_NAME, L, PRINT_FORMAT_NAMES, VIEW_NAMES)
from ..exceptions import CrossComputeDefinitionError
from ..macros import is_compatible_version, parse_number, split_path


VARIABLE_TEXT_PATTERN = re.compile(r'({[^}]+})')
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')


def load_definition(path, kinds=None):
    # TODO: Use strictyaml schemas
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
    if path.endswith('.yml'):
        raw_definition = strictyaml.load(text).data
    elif path.endswith('.json'):
        raw_definition = json.loads(text)
    else:
        raise CrossComputeDefinitionError({
            'path': 'must have extension .yml or .json'})
    check_dictionary(raw_definition, 'definition')
    try:
        protocol_name = raw_definition.pop('crosscompute')
    except KeyError:
        raise CrossComputeDefinitionError({'crosscompute': 'is required'})
    if not is_compatible_version(__version__, protocol_name):
        raise CrossComputeDefinitionError({
            'crosscompute': 'should be ' + __version__})
    return dict(raw_definition)


def normalize_definition(raw_definition, folder=None, kinds=None):
    try:
        kind = raw_definition['kind'].lower()
    except KeyError:
        raise CrossComputeDefinitionError({'kind': 'is required'})
    if kinds and kind not in kinds:
        raise CrossComputeDefinitionError({'kind': 'expected ' + ' or '.join(kinds)})
    if kind == 'project':
        definition = normalize_project_definition(raw_definition, folder)
    elif kind == 'automation':
        definition = normalize_automation_definition(raw_definition, folder)
    elif kind == 'result':
        definition = normalize_result_definition(raw_definition, folder)
    elif kind == 'tool':
        definition = normalize_tool_definition(raw_definition, folder)
    else:
        definition = raw_definition
    return definition


def normalize_project_definition(raw_project_definition, folder=None):
    project_definition = {'kind': 'project'}
    for key in ['id', 'name']:
        if key not in raw_project_definition:
            continue
        project_definition[key] = raw_project_definition[key]
    for key in ['tools', 'results', 'datasets']:
        if key not in raw_project_definition:
            continue
        resource_dictionaries = check_list(raw_project_definition[key], key)
        for resource_index, resource_dictionary in enumerate(
                resource_dictionaries):
            check_dictionary(
                resource_dictionary, key + f'[{resource_index}]')
        # project_definition[key] = {
        #    'id': _['id'] for _ in resource_dictionaries}
        project_definition[key] = [{'id': _['id']} for _ in resource_dictionaries]
    return project_definition


def normalize_automation_definition(raw_automation_definition, folder=None):
    try:
        path = join(folder, raw_automation_definition['path'])
    except KeyError as e:
        raise CrossComputeDefinitionError({e.args[0]: 'required'})
    return load_definition(path, kinds=['result', 'report'])


def normalize_result_definition(raw_result_definition, folder=None):
    if 'path' in raw_result_definition:
        result_definition_path = join(folder, raw_result_definition['path'])
        result_definition = load_definition(result_definition_path, kinds=['result'])
    else:
        result_definition = {'kind': 'result'}

    result_name = raw_result_definition.get(
        'name', result_definition.get('name', ''))
    if result_name:
        result_definition['name'] = result_name

    tool_definition = dict(raw_result_definition.get(
        'tool', result_definition.get('tool', {})))
    # TODO: Load tool by name
    if 'id' in tool_definition:
        tool_id = tool_definition['id']
        tool_version_id = tool_definition.get(
            'version', {}).get('id', 'latest')
        tool_definition = fetch_resource(
            'tools', tool_id + '/versions/' + tool_version_id)
    elif 'path' in tool_definition:
        tool_definition_path = join(folder, tool_definition['path'])
        tool_definition = load_definition(tool_definition_path)
    result_definition['tool'] = tool_definition

    raw_variable_dictionaries = sum([
        result_definition.get('input', {}).get('variables', []),
        raw_result_definition.get('input', {}).get('variables', []),
    ], [])
    variable_definitions = tool_definition.get(
        'input', {}).get('variables', [])
    result_definition['input'] = {
        'variables': normalize_result_variable_dictionaries(
            raw_variable_dictionaries, variable_definitions)}

    if 'print' in raw_result_definition:
        result_definition['print'] = get_print_dictionary(
            raw_result_definition['print'], folder)
    return result_definition


def normalize_result_variable_dictionaries(
        raw_variable_dictionaries, variable_definitions):
    try:
        raw_variable_dictionary_by_id = {
            _['id']: _ for _ in raw_variable_dictionaries}
    except KeyError:
        raise CrossComputeDefinitionError({
            'id': 'is required for each variable'})
    variable_definition_by_id = {_['id']: _ for _ in variable_definitions}
    variable_dictionaries = []
    for (
        variable_id, raw_variable_dictionary,
    ) in raw_variable_dictionary_by_id.items():
        try:
            variable_definition = variable_definition_by_id[variable_id]
        except KeyError:
            raise CrossComputeDefinitionError({
                'id': 'could not find variable ' + variable_id
                + ' in tool definition'})
        variable_view = variable_definition['view']
        try:
            variable_data = raw_variable_dictionary['data']
        except KeyError:
            raise CrossComputeDefinitionError({
                'data': 'is required for each variable'})
        variable_data = normalize_data(variable_data, variable_view)
        variable_dictionaries.append({
            'id': variable_id, 'data': variable_data})
    return variable_dictionaries


def normalize_tool_definition(dictionary, folder=None):
    d = {'kind': 'tool'}
    d.update(normalize_tool_definition_head(dictionary))
    d.update(normalize_tool_definition_body(dictionary, folder))
    return d


def normalize_tool_definition_head(dictionary):
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
    return d


def normalize_tool_definition_body(dictionary, folder=None):
    d = {}
    for key in ['input', 'output', 'log', 'debug']:
        if key not in dictionary:
            continue
        d[key] = get_put_dictionary(key, dictionary, folder)
    d['tests'] = normalize_test_dictionaries(dictionary.get(
        'tests', []))
    if 'script' in dictionary:
        d['script'] = get_script_dictionary(dictionary)
    if 'environment' in dictionary:
        d['environment'] = get_environment_dictionary(dictionary)
    return d


def normalize_version_dictionary(raw_version_dictionary):
    check_dictionary(raw_version_dictionary, 'version')
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


def normalize_data(raw_data, view_name):
    if isinstance(raw_data, dict):
        data = normalize_data_dictionary(raw_data, view_name)
    elif isinstance(raw_data, list):
        data = [normalize_data_dictionary(_, view_name) for _ in raw_data]
    else:
        raise CrossComputeDefinitionError({
            'data': 'must be a dictionary or list'})
    return data


def normalize_data_dictionary(raw_data_dictionary, view_name):
    check_dictionary(raw_data_dictionary, 'data')
    has_value = 'value' in raw_data_dictionary
    has_file = 'file' in raw_data_dictionary
    if not has_value and not has_file:
        raise CrossComputeDefinitionError({
            'data': 'must have value or file'})
    data_dictionary = {}
    if has_value:
        data_dictionary['value'] = normalize_value(
            raw_data_dictionary['value'], view_name)
    elif has_file:
        data_dictionary['file'] = normalize_file_dictionary(
            raw_data_dictionary['file'])
    return data_dictionary


def normalize_file_dictionary(raw_file_dictionary):
    check_dictionary(raw_file_dictionary, 'file')
    file_dictionary = {}
    try:
        file_id = raw_file_dictionary['id']
    except KeyError:
        raise CrossComputeDefinitionError({
            'id': 'is required for each file'})
    file_dictionary['id'] = file_id
    return file_dictionary


def normalize_value(raw_value, view_name):
    if view_name == 'number':
        try:
            value = parse_number(raw_value)
        except ValueError:
            raise CrossComputeDefinitionError({
                'value': f'could not parse number {raw_value}'})
    else:
        value = raw_value
    return value


def normalize_style_rule_strings(raw_style_rule_strings):
    check_list(raw_style_rule_strings, 'rules')
    try:
        style_text = '\n'.join(raw_style_rule_strings)
        style_rules = parse_stylesheet(
            style_text, skip_comments=True, skip_whitespace=True)
        style_rule_strings = [_.serialize() for _ in style_rules]
    except TypeError:
        raise CrossComputeDefinitionError({'rules': 'are bad'})
    return style_rule_strings


def normalize_tool_variable_dictionaries(
        raw_variable_dictionaries):
    variable_dictionaries = []
    for raw_variable_dictionary in raw_variable_dictionaries:
        try:
            variable_id = raw_variable_dictionary['id']
            variable_path = normalize_variable_path(
                raw_variable_dictionary['path'])
        except KeyError as e:
            raise CrossComputeDefinitionError({
                e.args[0]: 'is required for each variable'})
        variable_dictionary = {
            'id': variable_id,
            'name': raw_variable_dictionary.get('name') or get_name_from_id(
                variable_id),
            'view': raw_variable_dictionary.get('view') or DEFAULT_VIEW_NAME,
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
        except KeyError as e:
            raise CrossComputeDefinitionError({
                e.args[0]: 'is required for each template'})
        block_dictionaries = get_template_block_dictionaries(
            raw_template_dictionary, folder)
        if not block_dictionaries:
            continue
        template_dictionaries.append({
            'id': template_id,
            'name': raw_template_dictionary.get('name') or get_name_from_id(
                template_id),
            'blocks': block_dictionaries,
        })
    if not template_dictionaries:
        template_dictionaries.append({
            'id': 'generated',
            'name': 'Generated',
            'blocks': [{'id': _['id']} for _ in variable_dictionaries],
        })
    return template_dictionaries


def normalize_variable_path(variable_path):
    if '..' in split_path(variable_path):
        raise CrossComputeDefinitionError({
            'path': 'is bad ' + variable_path})
    return variable_path


def normalize_test_dictionaries(raw_test_dictionaries):
    check_list(raw_test_dictionaries, 'tests')
    if not raw_test_dictionaries:
        raise CrossComputeDefinitionError({
            'tests': 'must have at least one test defined'})
    try:
        test_dictionaries = [{
            'folder': _['folder'],
        } for _ in raw_test_dictionaries]
    except TypeError:
        raise CrossComputeDefinitionError({
            'tests': 'must be a list of dictionaries'})
    except KeyError as e:
        raise CrossComputeDefinitionError({
            e.args[0]: 'is required for each test'})
    return test_dictionaries


def normalize_script_dictionary(raw_script_dictionary):
    folder = raw_script_dictionary.get('folder', '.')
    try:
        command = raw_script_dictionary['command']
    except KeyError as e:
        raise CrossComputeDefinitionError({
            'script': 'requires ' + e.args[0]})
    return {
        'folder': folder,
        'command': command,
    }


def normalize_environment_dictionary(raw_environment_dictionary):
    try:
        image = raw_environment_dictionary['image']
        processor = raw_environment_dictionary['processor']
        memory = raw_environment_dictionary['memory']
    except KeyError as e:
        raise CrossComputeDefinitionError({
            'environment': 'requires ' + e.args[0]})
    return {
        'image': image,
        'processor': processor,
        'memory': memory,
    }


def normalize_block_dictionaries(raw_block_dictionaries, with_data=True):
    check_list(raw_block_dictionaries, 'blocks')
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
        elif with_data:
            raise CrossComputeDefinitionError({'data': 'is required'})
        block_dictionaries.append(block_dictionary)
    return block_dictionaries


def normalize_view_name(raw_view_name):
    if not isinstance(raw_view_name, str):
        raise CrossComputeDefinitionError({'view': 'must be a string'})

    view_name = raw_view_name.lower()
    if view_name not in VIEW_NAMES:
        raise CrossComputeDefinitionError({'view': 'must be ' + ' or '.join(VIEW_NAMES)})
    return view_name


def get_print_dictionary(dictionary, folder):
    print_dictionary = {}

    if 'style' in dictionary:
        raw_style_definition = dictionary['style']
        if 'path' in raw_style_definition:
            style_path = join(folder, raw_style_definition['path'])
            style_rules = load_style_rule_strings(style_path)
        style_rules += normalize_style_rule_strings(raw_style_definition.get('rules', []))
        style_definition = {'rules': style_rules}
        print_dictionary['style'] = style_definition

    if 'format' in dictionary:
        raw_format = dictionary['format']
        if raw_format not in PRINT_FORMAT_NAMES:
            raise CrossComputeDefinitionError({
                'format': 'must be ' + ' or '.join(PRINT_FORMAT_NAMES)})
        print_dictionary['format'] = raw_format

    return print_dictionary


def get_put_dictionary(key, dictionary, folder=None):
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
        variable_dictionaries = normalize_tool_variable_dictionaries(
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


def get_script_dictionary(dictionary):
    try:
        raw_script_dictionary = dictionary['script']
    except KeyError:
        L.warning('missing script definition')
        raw_script_dictionary = {}
    return normalize_script_dictionary(raw_script_dictionary)


def get_environment_dictionary(dictionary):
    try:
        raw_environment_dictionary = dictionary['environment']
    except KeyError:
        L.warning('missing environment definition')
        raw_environment_dictionary = {}
    return normalize_environment_dictionary(raw_environment_dictionary)


def get_template_block_dictionaries(dictionary, folder=None):
    if 'blocks' in dictionary:
        raw_block_dictionaries = dictionary['blocks']
    elif 'path' in dictionary and folder is not None:
        template_path = join(folder, dictionary['path'])
        raw_block_dictionaries = load_block_dictionaries(template_path)
    else:
        raw_block_dictionaries = []
    return normalize_block_dictionaries(
        raw_block_dictionaries, with_data=False)


def make_template_dictionary(variable_definitions):
    return {
        'id': 'generated',
        'name': 'Generated',
        'blocks': [{'id': _['id']} for _ in variable_definitions],
    }


def load_style_rule_strings(style_path):
    try:
        style_text = open(style_path, 'rt').read()
    except OSError:
        raise CrossComputeDefinitionError({'path': 'is bad ' + style_path})
    return normalize_style_rule_strings([style_text])


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


def check_dictionary(raw_value, value_name):
    if not isinstance(raw_value, dict):
        raise CrossComputeDefinitionError({value_name: 'must be a dictionary'})
    return raw_value


def check_list(raw_value, value_name):
    if not isinstance(raw_value, list):
        raise CrossComputeDefinitionError({value_name: 'must be a list'})
    return raw_value


def get_name_from_id(x_id):
    return normalize_key(
        x_id,
        separate_camel_case=True,
        separate_letter_digit=True,
    ).title()

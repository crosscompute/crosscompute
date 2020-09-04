import strictyaml
from os import environ
from os.path import dirname, join

from .constants import (
    HOST,
    L,
    VARIABLE_ID_PATTERN,
    VARIABLE_TEXT_PATTERN,
    VIEWS)
from .exceptions import CrossComputeConfigurationError


def get_crosscompute_host():
    return get_environment_variable('CROSSCOMPUTE_HOST', HOST)


def get_crosscompute_token():
    return get_environment_variable('CROSSCOMPUTE_TOKEN', required=True)


def get_environment_variable(name, default=None, required=False):
    try:
        value = environ[name]
    except KeyError:
        if required:
            exit(f'{name} is required in the environment')
        value = default
    return value


def load_tool_configuration(path):
    text = open(path, 'rt').read()
    dictionary = strictyaml.load(text).data
    if not isinstance(dictionary, dict):
        raise CrossComputeConfigurationError({'configuration': 'is invalid'})
    try:
        protocol = dictionary.pop('protocol')
    except KeyError:
        raise CrossComputeConfigurationError({'protocol': 'is required'})
    try:
        normalize_tool_configuration = {
            '0.8.3': normalize_tool_configuration_from_protocol_0_8_3,
        }[protocol]
    except KeyError:
        raise CrossComputeConfigurationError({'protocol': 'is invalid'})
    folder = dirname(path)
    return normalize_tool_configuration(dictionary, folder)


def normalize_tool_configuration_from_protocol_0_8_3(dictionary, folder):
    d = {}
    if 'id' in dictionary:
        d['id'] = dictionary['id']
    if 'slug' in dictionary:
        d['slug'] = dictionary['slug']
    try:
        d['name'] = dictionary['name']
        d['version'] = dictionary['version']
    except KeyError as e:
        raise CrossComputeConfigurationError({e.args[0]: 'is required'})
    d['input'] = normalize_put_configuration('input', dictionary, folder)
    d['output'] = normalize_put_configuration('output', dictionary, folder)
    # d['tests'] = normalize_tests_configuration('tests', dictionary)
    return d


def normalize_put_configuration(key, dictionary, folder=None):
    d = {}

    try:
        put_dictionary = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} configuration')
        return d

    try:
        variables = put_dictionary['variables']
    except KeyError:
        L.warning(f'missing {key} variables configuration')
        variables = []
    variables = normalize_variables(variables)
    if variables:
        d['variables'] = variables

    try:
        templates = put_dictionary['templates']
    except KeyError:
        L.warning(f'missing {key} templates configuration')
        templates = []
    templates = normalize_templates(templates, variables, folder)
    if templates:
        d['templates'] = templates

    return d


def normalize_tests_configuration(key, dictionary):
    try:
        raw_tests = dictionary[key]
    except KeyError:
        L.warning(f'missing {key} configuration')
    return normalize_tests(raw_tests)


def normalize_variables(raw_variables):
    variables = []
    for raw_variable in raw_variables:
        try:
            variables.append({
                'id': raw_variable['id'],
                'name': raw_variable['name'],
                'view': raw_variable['view'],
                'path': raw_variable['path'],
            })
        except KeyError as e:
            raise CrossComputeConfigurationError({
                e.args[0]: 'is required for each variable'})
    return variables


def normalize_templates(raw_templates, variables, folder=None):
    templates = []
    for raw_template in raw_templates:
        try:
            template_id = raw_template['id']
            template_name = raw_template['name']
        except KeyError as e:
            raise CrossComputeConfigurationError({
                e.args[0]: 'is required for each template'})
        template_blocks = normalize_blocks_configuration(
            'blocks', raw_template, variables, folder)
        if not template_blocks:
            continue
        templates.append({
            'id': template_id,
            'name': template_name,
            'blocks': template_blocks,
        })
    if not templates:
        templates.append({
            'id': 'generated',
            'name': 'Generated',
            'blocks': [{'id': _['id'] for _ in variables}],
        })
    return templates


def normalize_blocks_configuration(key, dictionary, variables, folder=None):
    blocks = []
    if 'blocks' in dictionary:
        blocks = dictionary['blocks']
    elif 'path' in dictionary and folder is not None:
        template_path = join(folder, dictionary['path'])
        blocks = load_blocks(template_path)
    return normalize_blocks(blocks, variables)


def load_blocks(template_path):
    try:
        template_text = open(template_path, 'rt').read()
    except IOError:
        raise CrossComputeConfigurationError({
            'path': f'is invalid for template {template_path}'})
    return parse_blocks(template_text)


def parse_blocks(template_text):
    blocks = []
    for text in VARIABLE_TEXT_PATTERN.split(template_text):
        text = text.strip()
        if not text:
            continue
        match = VARIABLE_ID_PATTERN.match(text)
        if match:
            variable_id = match.group(1)
            blocks.append({'id': variable_id})
            continue
        blocks.append({'view': 'markdown', 'data': {'value': text}})
    return blocks


def normalize_blocks(blocks, variables):
    ds = []
    for block in blocks:
        if 'id' in block:
            ds.append({'id': block['id']})
            continue
        d = {}
        try:
            raw_view = block['view']
            raw_data = block['data']
        except KeyError as e:
            raise CrossComputeConfigurationError({
                e.args[0]: 'is required for each block that lacks an id'})
        view = normalize_view(raw_view)
        data = normalize_data(raw_data, view)
        d['view'] = view
        d['data'] = data
        ds.append(d)
    return ds


def normalize_tests(raw_tests):
    # TODO: Normalize tests
    return [dict(_) for _ in raw_tests]


def normalize_view(raw_view):
    if not isinstance(raw_view, str):
        raise CrossComputeConfigurationError({'view': 'must be a string'})

    view = raw_view.lower()
    if view not in VIEWS:
        raise CrossComputeConfigurationError({
            'view': 'must be one of ' + ' '.join(VIEWS)})
    return view


def normalize_data(raw_data, view):
    if not isinstance(raw_data, dict):
        raise CrossComputeConfigurationError({
            'data': 'must be a dictionary'})
    if 'value' not in raw_data and 'file' not in raw_data:
        raise CrossComputeConfigurationError({
            'data': 'must contain either a file or value'})

    data = {}
    if 'value' in raw_data:
        data['value'] = normalize_value(raw_data['value'], view)
    elif 'file' in raw_data:
        data['file'] = normalize_file(raw_data['file'])
    return data


def normalize_value(raw_value, view=None):
    # TODO: Normalize value based on view
    return raw_value


def normalize_file(raw_file):
    # TODO: Normalize file
    return raw_file


def get_resource_url(host, resource_name, resource_id=None):
    url = host + '/' + resource_name
    if resource_id:
        url += '/' + resource_id
    return url + '.json'

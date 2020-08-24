import strictyaml
from os import environ
from os.path import dirname, join

from .constants import L, VARIABLE_ID_PATTERN, VARIABLE_TEXT_PATTERN
from .exceptions import CrossComputeConfigurationError


def get_crosscompute_token():
    name = 'CROSSCOMPUTE_TOKEN'
    try:
        token = environ[name]
    except KeyError:
        exit(f'{name} is required in the environment')
    return token


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


def normalize_put_configuration(key, dictionary, folder):
    d = {}
    try:
        put_dictionary = dictionary[key]
    except KeyError:
        L.warn(f'missing {key} configuration')
        return d

    try:
        variables = put_dictionary['variables']
    except KeyError:
        L.warn(f'missing {key} variables configuration')
        variables = []
    variables = normalize_variables(variables)
    if variables:
        d['variables'] = variables

    try:
        templates = put_dictionary['templates']
    except KeyError:
        L.warn(f'missing {key} variables configuration')
        templates = []
    templates = normalize_templates(templates, variables, folder)
    if templates:
        d['templates'] = templates

    return d


def normalize_tests_configuration(key, dictionary):
    # TODO: Validate
    try:
        d = dictionary[key]
    except KeyError:
        L.warn(f'missing {key} configuration')
    return [dict(_) for _ in d]


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
                e.args[0]: 'is required for each variable',
            })
    return variables


def normalize_templates(raw_templates, variables, folder):
    templates = []
    for raw_template in raw_templates:
        try:
            template_name = raw_template['name']
            template_path = join(folder, raw_template['path'])
        except KeyError as e:
            raise CrossComputeConfigurationError({
                e.args[0]: 'is required for each template',
            })
        try:
            template_text = open(template_path, 'rt').read()
        except IOError:
            raise CrossComputeConfigurationError({
                'path': f'is invalid for template: {template_path}',
            })
        templates.append({
            'name': template_name,
            'blocks': parse_blocks(template_text),
        })
    if not templates:
        templates.append({
            'id': 'generated',
            'name': 'Generated',
            'blocks': [{'id': _['id'] for _ in variables}],
        })
    return templates


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

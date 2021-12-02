import logging
import tomli
import yaml
from configparser import ConfigParser
from os.path import basename, dirname, exists, join, splitext

from ..constants import (
    AUTOMATION_ROUTE,
    AUTOMATION_NAME,
    BATCH_ROUTE,
    PAGE_TYPE_NAMES,
    STYLE_ROUTE)
from ..exceptions import CrossComputeConfigurationError
from ..macros import get_slug_from_name


def load_configuration(configuration_path):
    file_extension = splitext(configuration_path)[1]
    try:
        configuration_format = {
            '.cfg': 'ini',
            '.ini': 'ini',
            '.toml': 'toml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }[file_extension]
    except KeyError:
        raise CrossComputeConfigurationError(
            f'{file_extension} configuration not supported')
    load_raw_configuration = {
        'ini': load_raw_configuration_ini,
        'toml': load_raw_configuration_toml,
        'yaml': load_raw_configuration_yaml,
    }[configuration_format]
    configuration = load_raw_configuration(configuration_path)
    configuration['folder'] = dirname(configuration_path) or '.'
    return configuration


def load_raw_configuration_ini(configuration_path):
    configuration = ConfigParser()
    configuration.read(configuration_path)
    return configuration


def load_raw_configuration_toml(configuration_path):
    with open(configuration_path, 'rt') as configuration_file:
        configuration = tomli.load(configuration_file)
    return configuration


def load_raw_configuration_yaml(configuration_path):
    with open(configuration_path, 'rt') as configuration_file:
        configuration = yaml.safe_load(configuration_file)
    return configuration


def get_automation_definitions(configuration):
    automation_definitions = []
    for automation_configuration in get_automation_configurations(
            configuration):
        if 'output' not in automation_configuration:
            continue
        automation_name = automation_configuration.get(
            'name', AUTOMATION_NAME.format(automation_index=0))
        automation_slug = automation_configuration.get(
            'slug', get_slug_from_name(automation_name))
        automation_uri = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)
        automation_configuration.update({
            'name': automation_name,
            'slug': automation_slug,
            'uri': automation_uri,
            'batches': get_batch_definitions(automation_configuration),
            'display': get_display_configuration(automation_configuration),
        })
        automation_definitions.append(automation_configuration)
    return automation_definitions


def get_automation_configurations(configuration):
    automation_configurations = []
    configurations = [configuration]
    while configurations:
        c = configurations.pop(0)
        folder = c['folder']
        for import_configuration in c.get('imports', []):
            if 'path' in import_configuration:
                path = import_configuration['path']
                automation_configuration = load_configuration(join(
                    folder, path))
            else:
                logging.error(
                    'path or folder or uri or name required for each import')
                continue
            automation_configuration['parent'] = c
            configurations.append(automation_configuration)
        automation_configurations.append(c)
    return automation_configurations


def get_batch_definitions(configuration):
    batch_definitions = []
    for batch_configuration in configuration.get('batches', []):
        try:
            batch_folder = batch_configuration['folder']
        except KeyError:
            logging.error('folder required for each batch')
            continue
        batch_name = batch_configuration.get(
            'name', basename(batch_folder))
        batch_slug = batch_configuration.get(
            'slug', get_slug_from_name(batch_name))
        batch_uri = BATCH_ROUTE.format(batch_slug=batch_slug)
        batch_configuration.update({
            'name': batch_name,
            'slug': batch_slug,
            'uri': batch_uri,
        })
        batch_definitions.append(batch_configuration)
    return batch_definitions


def get_raw_variable_definitions(configuration, page_type_name):
    return configuration.get(page_type_name, {}).get('variables', [])


def get_all_variable_definitions(configuration, page_type_name):
    variable_definitions = get_raw_variable_definitions(
        configuration, page_type_name).copy()
    for type_name in PAGE_TYPE_NAMES[:2]:
        if type_name == page_type_name:
            continue
        variable_definitions.extend(get_raw_variable_definitions(
            configuration, type_name))
    return variable_definitions


def get_template_texts(configuration, page_type_name):
    template_texts = []
    folder = configuration['folder']
    page_configuration = configuration.get(page_type_name, {})
    for template_definition in page_configuration.get('templates', []):
        try:
            template_path = template_definition['path']
        except KeyError:
            logging.error('path required for each template')
            continue
        try:
            path = join(folder, template_path)
            template_file = open(path, 'rt')
        except OSError:
            logging.error(f'{path} does not exist or is not accessible')
            continue
        template_text = template_file.read().strip()
        if not template_text:
            continue
        template_texts.append(template_text)
    if not template_texts:
        variable_definitions = get_raw_variable_definitions(
            configuration, page_type_name)
        variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
        template_texts = [' '.join('{' + _ + '}' for _ in variable_ids)]
    return template_texts


def get_css_uris(configuration):
    has_parent = 'parent' in configuration
    display_configuration = configuration.get('display', {})
    css_uris = []
    for style_definition in display_configuration.get('styles', []):
        style_uri = style_definition['uri']
        is_relative = r'//' not in style_uri
        if has_parent and is_relative:
            style_uri = configuration['uri'] + style_uri
        css_uris.append(style_uri)
    return css_uris


def get_display_configuration(configuration):
    folder = configuration['folder']
    display_configuration = configuration.get('display', {})
    for style_definition in display_configuration.get('styles', []):
        uri = style_definition.get('uri', '').strip()
        path = style_definition.get('path', '').strip()
        if not uri and not path:
            logging.error('uri or path required for each style')
            continue
        if path:
            if not exists(join(folder, path)):
                logging.error('style not found at path %s', path)
            style_definition['uri'] = STYLE_ROUTE.format(
                style_path=path)
    return display_configuration

# TODO: Save to yaml, ini, toml
import tomli
from configparser import ConfigParser
from invisibleroads_macros_log import format_path
from logging import getLogger
from os.path import abspath, basename, dirname, exists, join, splitext
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from time import time

from .. import __version__
from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    MODE_NAMES,
    STYLE_ROUTE)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from ..macros.web import format_slug
from .variable import (
    format_text,
    yield_data_by_id_from_csv,
    yield_data_by_id_from_txt)


def load_configuration(configuration_path):
    configuration_path = abspath(configuration_path)
    configuration_format = get_configuration_format(configuration_path)
    load_raw_configuration = {
        'ini': load_raw_configuration_ini,
        'toml': load_raw_configuration_toml,
        'yaml': load_raw_configuration_yaml,
    }[configuration_format]
    configuration = load_raw_configuration(configuration_path)
    configuration['folder'] = dirname(configuration_path)
    configuration['path'] = configuration_path
    configuration = validate_configuration(configuration)
    L.debug(f'{format_path(configuration_path)} loaded')
    return configuration


def get_configuration_format(path):
    file_extension = splitext(path)[1]
    try:
        configuration_format = {
            '.cfg': 'ini',
            '.ini': 'ini',
            '.toml': 'toml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }[file_extension]
    except KeyError:
        raise CrossComputeError(
            f'{file_extension} format not supported for configuration'.strip())
    return configuration_format


def validate_configuration(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute']
    if protocol_version != __version__:
        raise CrossComputeConfigurationError(
            f'crosscompute {protocol_version} != {__version__}; '
            f'pip install crosscompute=={protocol_version}')
    for mode_name in MODE_NAMES:
        mode_configuration = configuration.get(mode_name, {})
        for variable_definition in mode_configuration.get('variables', []):
            try:
                variable_definition['id']
                variable_definition['view']
                variable_definition['path']
            except KeyError as e:
                raise CrossComputeConfigurationError(
                    f'{e} required for each variable')
    return configuration


def save_raw_configuration_yaml(configuration_path, configuration):
    yaml = YAML()
    try:
        with open(configuration_path, 'wt') as configuration_file:
            yaml.dump(configuration, configuration_file)
    except (OSError, YAMLError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration_path


def load_raw_configuration_ini(configuration_path):
    configuration = ConfigParser()
    try:
        paths = configuration.read(configuration_path)
    except (OSError, UnicodeDecodeError) as e:
        raise CrossComputeConfigurationError(e)
    if not paths:
        raise CrossComputeConfigurationError(f'{configuration_path} not found')
    return dict(configuration)


def load_raw_configuration_toml(configuration_path):
    try:
        with open(configuration_path, 'rt') as configuration_file:
            configuration = tomli.load(configuration_file)
    except (OSError, UnicodeDecodeError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration


def load_raw_configuration_yaml(configuration_path, with_comments=False):
    yaml = YAML(typ='rt' if with_comments else 'safe')
    try:
        with open(configuration_path, 'rt') as configuration_file:
            configuration = yaml.load(configuration_file)
    except (OSError, YAMLError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration or {}


def get_automation_definitions(configuration):
    automation_definitions = []
    for automation_index, automation_configuration in enumerate(
            get_automation_configurations(configuration)):
        if 'output' not in automation_configuration:
            continue
        automation_name = automation_configuration.get(
            'name', make_automation_name(automation_index))
        automation_slug = automation_configuration.get(
            'slug', format_slug(automation_name))
        automation_uri = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)
        automation_configuration['name'] = automation_name
        automation_configuration['slug'] = automation_slug
        automation_configuration['uri'] = automation_uri
        automation_configuration.update({
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
            elif 'uri' in import_configuration:
                L.error('uri import not supported yet')
                continue
            elif 'name' in import_configuration:
                L.error('name import not supported yet')
                continue
            else:
                L.error('path or uri or name required for each import')
                continue
            automation_configuration['parent'] = c
            configurations.append(automation_configuration)
        automation_configurations.append(c)
    return automation_configurations


def make_automation_name(automation_index):
    return AUTOMATION_NAME.replace('X', str(automation_index))


def get_batch_definitions(configuration):
    batch_definitions = []
    automation_folder = configuration['folder']
    variable_definitions = get_variable_definitions(
        configuration, 'input')
    for raw_batch_definition in configuration.get('batches', []):
        try:
            batch_definition = normalize_batch_definition(raw_batch_definition)
            if 'configuration' in raw_batch_definition:
                batch_configuration = raw_batch_definition['configuration']
                if 'path' in batch_configuration:
                    definitions = get_batch_definitions_from_path(join(
                        automation_folder, batch_configuration['path'],
                    ), batch_definition, variable_definitions)
                # TODO: Support batch_configuration['uri']
                else:
                    raise CrossComputeConfigurationError(
                        'path expected for each batch configuration')
            else:
                batch_slug = batch_definition['slug'] or format_slug(
                    batch_definition['name'])
                batch_definition['slug'] = batch_slug
                batch_definition['uri'] = BATCH_ROUTE.format(
                    batch_slug=batch_slug)
                definitions = [batch_definition]
        except CrossComputeConfigurationError as e:
            L.error(e)
            continue
        batch_definitions.extend(definitions)
    return batch_definitions


def get_css_uris(configuration):
    style_definitions = configuration.get('display', {}).get('styles', [])
    return [_['uri'] for _ in style_definitions]


def get_display_configuration(configuration):
    folder = configuration['folder']
    display_configuration = configuration.get('display', {})
    has_parent = 'parent' in configuration
    automation_uri = configuration['uri']
    for style_definition in display_configuration.get('styles', []):
        style_uri = style_definition.get('uri', '').strip()
        style_path = style_definition.get('path', '').strip()
        if '//' in style_uri:
            continue
        if not style_uri and not style_path:
            L.error('uri or path required for each style')
            continue
        path = join(folder, style_path)
        if not exists(path):
            L.error('style not found at path %s', path)
            continue
        style_name = '%s-%s.css' % (splitext(style_path)[0], time())
        style_uri = STYLE_ROUTE.format(style_name=style_name)
        if has_parent:
            style_uri = automation_uri + style_uri
        style_definition['uri'] = style_uri
    return display_configuration


def get_variable_definitions(configuration, mode_name, with_all=False):
    mode_configuration = configuration.get(mode_name, {})
    variable_definitions = mode_configuration.get('variables', [])
    for variable_definition in variable_definitions:
        variable_definition['mode'] = mode_name
    if with_all:
        variable_definitions = variable_definitions.copy()
        for MODE_NAME in MODE_NAMES:
            if mode_name == MODE_NAME:
                continue
            variable_definitions.extend(get_variable_definitions(
                configuration, MODE_NAME))
    return variable_definitions


def get_template_texts(configuration, mode_name):
    template_texts = []
    folder = configuration['folder']
    mode_configuration = configuration.get(mode_name, {})
    for template_definition in mode_configuration.get('templates', []):
        try:
            template_path = template_definition['path']
        except KeyError:
            L.error('path required for each template')
            continue
        try:
            path = join(folder, template_path)
            template_file = open(path, 'rt')
        except OSError:
            L.error('%s does not exist or is not accessible', path)
            continue
        template_text = template_file.read().strip()
        if not template_text:
            continue
        template_texts.append(template_text)
    if not template_texts:
        variable_definitions = get_variable_definitions(
            configuration, mode_name)
        variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
        template_texts = ['\n'.join('{%s}' % _ for _ in variable_ids)]
    return template_texts


def normalize_batch_definition(batch_definition):
    try:
        batch_folder = get_scalar_text(batch_definition, 'folder')
    except KeyError:
        raise CrossComputeConfigurationError('folder required for each batch')
    batch_name = get_scalar_text(batch_definition, 'name', basename(
        batch_folder))
    batch_slug = get_scalar_text(batch_definition, 'slug', '')
    return {
        'folder': batch_folder,
        'name': batch_name,
        'slug': batch_slug,
    }


def get_batch_definitions_from_path(
        path, batch_definition, variable_definitions):
    file_extension = splitext(path)[1]
    try:
        yield_data_by_id = {
            '.csv': yield_data_by_id_from_csv,
            '.txt': yield_data_by_id_from_txt,
        }[file_extension]
    except KeyError:
        raise CrossComputeConfigurationError(
            f'{file_extension} not supported for batch configuration')
    batch_folder = batch_definition['folder']
    batch_name = batch_definition['name']
    batch_slug = batch_definition['slug']
    batch_definitions = []
    for data_by_id in yield_data_by_id(path, variable_definitions):
        folder = format_text(batch_folder, data_by_id)
        name = format_text(batch_name, data_by_id)
        slug = format_text(
            batch_slug, data_by_id) if batch_slug else format_slug(name)
        batch_definitions.append(batch_definition | {
            'folder': folder, 'name': name, 'slug': slug,
            'uri': BATCH_ROUTE.format(batch_slug=slug),
            'data_by_id': data_by_id})
    return batch_definitions


def get_scalar_text(configuration, key, default=None):
    value = configuration.get(key, default)
    if value is None:
        raise KeyError
    if isinstance(value, dict):
        L.warning('surround text with quotes if it begins with a {')
        value = '{%s}' % list(value.keys())[0]
    return value


L = getLogger(__name__)

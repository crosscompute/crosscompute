# TODO: Save to yaml, ini, toml
import tomli
from configparser import ConfigParser
from copy import deepcopy
from invisibleroads_macros_log import format_path
from logging import getLogger
from os.path import abspath, join, splitext
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ..constants import (
    MODE_NAMES)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from .validation import AutomationDefinition


def load_configuration(configuration_path, index=0):
    configuration_path = abspath(configuration_path)
    configuration_format = get_configuration_format(configuration_path)
    load_raw_configuration = {
        'ini': load_raw_configuration_ini,
        'toml': load_raw_configuration_toml,
        'yaml': load_raw_configuration_yaml,
    }[configuration_format]
    configuration = load_raw_configuration(configuration_path)
    try:
        configuration = AutomationDefinition(
            configuration,
            path=configuration_path,
            index=index)
    except CrossComputeConfigurationError as e:
        if not hasattr(e, 'path'):
            e.path = configuration_path
        raise
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
        automation_definitions.append(automation_configuration)
    return automation_definitions


def get_automation_configurations(configuration):
    automation_configurations = []
    configurations = [deepcopy(configuration)]
    while configurations:
        c = configurations.pop(0)
        folder = c.folder
        for i, import_configuration in enumerate(c.get('imports', []), 1):
            if 'path' in import_configuration:
                path = import_configuration['path']
                automation_configuration = load_configuration(join(
                    folder, path), index=i)
            else:
                L.error('path or uri or name required for each import')
                continue
            configurations.append(automation_configuration)
        automation_configurations.append(c)
    return automation_configurations


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
    folder = configuration.folder
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


L = getLogger(__name__)

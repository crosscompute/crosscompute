from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from logging import getLogger
from os import environ
from os.path import relpath, splitext
from time import time

from .. import __version__
from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    MODE_NAMES,
    STYLE_ROUTE)
from ..macros.web import format_slug
from .variable import VARIABLE_VIEW_BY_NAME


def validate_protocol(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute']
    if protocol_version != __version__:
        raise CrossComputeConfigurationError(
            f'crosscompute {protocol_version} != {__version__}; '
            f'pip install crosscompute=={protocol_version}')
    return {}


def validate_identifiers(configuration):
    index = configuration.index
    name = configuration.get('name', make_automation_name(index))
    slug = configuration.get('slug', format_slug(name))
    uri = AUTOMATION_ROUTE.format(automation_slug=slug)
    return {
        'name': name,
        'slug': slug,
        'uri': uri,
    }


def validate_variable_definitions(configuration):
    view_names = []
    for mode_name in MODE_NAMES:
        mode_configuration = get_dictionary(configuration, mode_name)
        variable_definitions = get_dictionaries(
            mode_configuration, 'variables')
        variable_ids = []
        for variable_definition in variable_definitions:
            try:
                variable_id = variable_definition['id']
                view_name = variable_definition['view']
                variable_path = variable_definition['path']
            except KeyError as e:
                raise CrossComputeConfigurationError(
                    f'{e} required for each variable')
            if variable_id in variable_ids:
                raise CrossComputeConfigurationError(
                    f'duplicate variable id {variable_id} in {mode_name}')
            if relpath(variable_path).startswith('..'):
                raise CrossComputeConfigurationError(
                    f'{variable_path} cannot reference parent folder')
            variable_ids.append(variable_id)
            view_names.append(view_name)
    L.debug('view_names =', view_names)
    return {
        '___view_names': view_names,
    }


def validate_variable_views(configuration):
    variable_ids = set()
    for view_name in configuration.___view_names:
        try:
            View = VARIABLE_VIEW_BY_NAME[view_name]
        except KeyError:
            raise CrossComputeConfigurationError(f'{view_name} not installed')
        d = check_environment_variable_definitions(
            View.environment_variable_definitions)
        variable_ids.update(d['___environment_variable_ids'])
    return {}


def validate_batch_definitions(configuration):
    batch_definitions = get_dictionaries(configuration, 'batches')
    for batch_definition in batch_definitions:
        try:
            batch_definition['folder']
        except KeyError as e:
            raise CrossComputeConfigurationError(
                f'{e} required for each batch')
    return {}


def validate_environment_variable_definitions(configuration):
    variable_ids = set()
    environment_configuration = get_dictionary(configuration, 'environment')
    environment_variable_definitions = get_dictionaries(
        environment_configuration, 'variables')
    d = check_environment_variable_definitions(
        environment_variable_definitions)
    variable_ids.update(d['___environment_variable_ids'])
    return {}


def validate_display_configuration(configuration):
    style_definitions = []
    display_configuration = get_dictionary(configuration, 'display')
    raw_style_definitions = get_dictionaries(display_configuration, 'styles')
    automation_folder = configuration.folder
    automation_index = configuration.index
    automation_uri = configuration.uri
    for raw_style_definition in raw_style_definitions:
        style_uri = raw_style_definition.get('uri', '').strip()
        style_path = raw_style_definition.get('path', '').strip()
        if not style_uri and not style_path:
            raise CrossComputeConfigurationError(
                'uri or path required for each style')
        style_definition = {'uri': style_uri}
        if '//' not in style_uri:
            path = automation_folder / style_path
            if not path.exists():
                raise CrossComputeConfigurationError(
                    f'style not found at {path}')
            style_name = '%s-%s.css' % (format_slug(splitext(
                style_path)[0]), time())
            style_uri = STYLE_ROUTE.format(style_name=style_name)
            if automation_index > 0:
                style_uri = automation_uri + style_uri
            style_definition.update({'uri': style_uri, 'path': style_path})
        style_definitions.append(style_definition)
    return {
        'style_definitions': style_definitions,
    }


def check_environment_variable_definitions(environment_variable_definitions):
    variable_ids = set()
    for environment_variable_definition in environment_variable_definitions:
        try:
            variable_id = environment_variable_definition['id']
        except KeyError as e:
            raise CrossComputeConfigurationError(
                f'{e} required for each environment variable')
        try:
            environ[variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'{variable_id} is missing in the environment')
        variable_ids.add(variable_id)
    L.debug('environment_variable_ids =', variable_ids)
    return {
        '___environment_variable_ids': variable_ids,
    }


def make_automation_name(automation_index):
    return AUTOMATION_NAME.replace('X', str(automation_index))


def get_dictionaries(d, key):
    values = get_list(d, key)
    for value in values:
        if not isinstance(value, dict):
            raise CrossComputeConfigurationError(f'{key} must be dictionaries')
    return values


def get_dictionary(d, key):
    value = d.get(key, {})
    if not isinstance(value, dict):
        raise CrossComputeConfigurationError(f'{key} must be a dictionary')
    return value


def get_list(d, key):
    value = d.get(key, [])
    if not isinstance(value, list):
        raise CrossComputeConfigurationError(f'{key} must be a list')
    return value


AUTOMATION_DEFINITION_VALIDATION_FUNCTIONS = [
    validate_protocol,
    validate_identifiers,
    validate_variable_definitions,
    validate_variable_views,
    validate_batch_definitions,
    validate_environment_variable_definitions,
    validate_display_configuration,
]
L = getLogger(__name__)

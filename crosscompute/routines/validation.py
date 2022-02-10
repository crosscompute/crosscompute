from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from os import environ
from os.path import relpath

from .. import __version__
from ..constants import (
    MODE_NAMES)
from .variable import VARIABLE_VIEW_BY_NAME


def validate_protocol(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute']
    if protocol_version != __version__:
        raise CrossComputeConfigurationError(
            f'crosscompute {protocol_version} != {__version__}; '
            f'pip install crosscompute=={protocol_version}')
    return {
        '___protocol_version': protocol_version,
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
    return {
        '___view_names': view_names,
    }


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
    environment_configuration = get_dictionary(configuration, 'environment')
    environment_variable_definitions = get_dictionaries(
        environment_configuration, 'variables')
    d = check_environment_variable_definitions(
        environment_variable_definitions)
    return d


def validate_variable_views(configuration):
    environment_variable_ids = configuration.___environment_variable_ids
    for view_name in configuration.___view_names:
        try:
            View = VARIABLE_VIEW_BY_NAME[view_name]
        except KeyError:
            raise CrossComputeConfigurationError(f'{view_name} not installed')
        d = check_environment_variable_definitions(
            View.environment_variable_definitions)
        environment_variable_ids.update(d['___environment_variable_ids'])
    return {
        '___environment_variable_ids': environment_variable_ids
    }


def check_environment_variable_definitions(environment_variable_definitions):
    environment_variable_ids = set()
    for environment_variable_definition in environment_variable_definitions:
        try:
            environment_variable_id = environment_variable_definition['id']
        except KeyError as e:
            raise CrossComputeConfigurationError(
                f'{e} required for each environment variable')
        try:
            environ[environment_variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'{environment_variable_id} is missing in the environment')
        environment_variable_ids.add(environment_variable_id)
    return {
        '___environment_variable_ids': environment_variable_ids,
    }


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
    validate_variable_definitions,
    validate_batch_definitions,
    validate_environment_variable_definitions,
    validate_variable_views,
]

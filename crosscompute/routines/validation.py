from collections import Counter
from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from logging import getLogger
from os import environ
from os.path import relpath, splitext
from pathlib import Path
from time import time

from .. import __version__
from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    MODE_NAMES,
    STYLE_ROUTE)
from ..macros.web import format_slug
from .variable import VARIABLE_VIEW_BY_NAME


class Definition(dict):

    def __init__(self, d, **kwargs):
        super().__init__(d)
        self._initialize(kwargs)
        self._validate()

    def _initialize(self, kwargs):
        self._validation_functions = []

    def _validate(self):
        for f in self._validation_functions:
            self.__dict__.update(f(self))
        for k in self.__dict__.copy():
            if k.startswith('___'):
                del self.__dict__[k]


class AutomationDefinition(Definition):

    def _initialize(self, kwargs):
        self.path = path = Path(kwargs['path'])
        self.folder = path.parents[0]
        self.index = kwargs['index']
        self._validation_functions = [
            validate_protocol,
            validate_automation_identifiers,
            validate_variable_definitions,
            validate_variable_views,
            validate_batch_definitions,
            validate_environment_variable_definitions,
            validate_display_configuration,
        ]

    def get_variable_definitions(self, mode_name):
        return self.variable_definitions_by_mode_name[mode_name]

    '''
    def get_template_text(self, mode_name):
        template_definitions = self.template_definitions_by_mode_name[
            mode_name]
        # !!!
        return '\n'.join(get_template_texts(self, mode_name))
    '''


class TemplateDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_template_identifiers,
        ]


class VariableDefinition(Definition):

    def _initialize(self, kwargs):
        self.mode_name = kwargs['mode_name']
        self._validation_functions = [
            validate_variable_identifiers,
            validate_variable_configuration,
        ]


class BatchDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_batch_identifiers,
        ]


def validate_protocol(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute']
    if protocol_version != __version__:
        raise CrossComputeConfigurationError(
            f'crosscompute {protocol_version} != {__version__}; '
            f'pip install crosscompute=={protocol_version}')
    return {}


def validate_automation_identifiers(configuration):
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
    variable_definitions_by_mode_name = {}
    view_names = []
    for mode_name in MODE_NAMES:
        mode_configuration = get_dictionary(configuration, mode_name)
        variable_definitions = [VariableDefinition(
            _, mode_name=mode_name,
        ) for _ in get_dictionaries(mode_configuration, 'variables')]
        variable_ids = [_.id for _ in variable_definitions]
        for variable_id, count in Counter(variable_ids).items():
            if count > 1:
                raise CrossComputeConfigurationError(
                    f'duplicate variable id {variable_id} in {mode_name}')
        variable_definitions_by_mode_name[mode_name] = variable_definitions
        view_names = [_.view_name for _ in variable_definitions]
    L.debug('view_names =', view_names)
    return {
        'variable_definitions_by_mode_name': variable_definitions_by_mode_name,
        '___view_names': view_names,
    }


def validate_variable_views(configuration):
    for view_name in configuration.___view_names:
        try:
            View = VARIABLE_VIEW_BY_NAME[view_name]
        except KeyError:
            raise CrossComputeConfigurationError(f'{view_name} not installed')
        get_environment_variable_ids(View.environment_variable_definitions)
    return {}


def validate_batch_definitions(configuration):
    batch_definitions = []
    raw_batch_definitions = get_dictionaries(configuration, 'batches')
    automation_folder = configuration.folder
    variable_definitions = configuration.get_variable_definitions('input')
    for raw_batch_definition in raw_batch_definitions:
        if 'configuration' in raw_batch_definition:
            batch_configuration = raw_batch_definition['configuration']
            if 'path' in batch_configuration:
                new_batch_definitions = get_batch_definitions_from_path(
                    automation_folder / batch_configuration['path'],
                    raw_batch_definition, variable_definitions)
            else:
                raise CrossComputeConfigurationError(
                    'path expected for each batch configuration')
        else:
            new_batch_definitions = [BatchDefinition(raw_batch_definition)]
        batch_definitions.extend(new_batch_definitions)

    return {
        'batch_definitions': batch_definitions,
    }


def validate_environment_variable_definitions(configuration):
    environment_configuration = get_dictionary(configuration, 'environment')
    environment_variable_definitions = get_dictionaries(
        environment_configuration, 'variables')
    get_environment_variable_ids(environment_variable_definitions)
    return {}


def validate_display_configuration(configuration):
    style_definitions = []
    display_configuration = get_dictionary(configuration, 'display')
    raw_style_definitions = get_dictionaries(display_configuration, 'styles')
    automation_folder = configuration.folder
    automation_index = configuration.index
    automation_uri = configuration.uri
    reference_time = time()
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
            style_name = format_slug(
                f'{splitext(style_path)[0]}-{reference_time}')
            style_uri = STYLE_ROUTE.format(style_name=style_name)
            if automation_index > 0:
                style_uri = automation_uri + style_uri
            style_definition.update({'uri': style_uri, 'path': style_path})
        style_definitions.append(style_definition)
    css_uris = [_['uri'] for _ in style_definitions]
    return {
        'style_definitions': style_definitions,
        'css_uris': css_uris,
    }


def validate_template_identifiers():
    pass


def validate_variable_identifiers(variable_definition):
    try:
        variable_id = variable_definition['id']
        view_name = variable_definition['view']
        variable_path = variable_definition['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each variable')
    if relpath(variable_path).startswith('..'):
        raise CrossComputeConfigurationError(
            f'{variable_path} cannot reference parent folder')
    return {
        'id': variable_id,
        'view_name': view_name,
        'path': variable_path,
    }


def validate_variable_configuration(variable_definition):
    variable_configuration = get_dictionary(
        variable_definition, 'configuration')
    return {
        'configuration': variable_configuration,
    }


def validate_batch_identifiers(batch_definition):
    try:
        folder = Path(get_scalar_text(batch_definition, 'folder'))
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each batch')
    name = get_scalar_text(batch_definition, 'name', folder.name)
    slug = get_scalar_text(batch_definition, 'slug', name)
    d = {
        'folder': folder,
        'name': name,
        'slug': slug,
    }
    if 'configuration' not in batch_definition:
        slug = format_slug(slug)
        d.update({
            'slug': slug,
            'uri': BATCH_ROUTE.format(batch_slug=slug)})
    return d


def get_environment_variable_ids(environment_variable_definitions):
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
    return variable_ids


def get_scalar_text(d, key, default=None):
    value = d.get(key) or default
    if value is None:
        raise KeyError(key)
    if isinstance(value, dict):
        raise CrossComputeConfigurationError(
            f'surround {key} with quotes since it begins with a {{')
    return value


def get_batch_definitions_from_path(
        batch_configuration_path, raw_batch_definition, variable_definitions):
    return []


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


L = getLogger(__name__)

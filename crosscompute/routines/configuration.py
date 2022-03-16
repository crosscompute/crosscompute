# TODO: Save to ini, toml
import tomli
from collections import Counter
from configparser import ConfigParser
from invisibleroads_macros_log import format_path
from logging import getLogger
from nbconvert import PythonExporter
from nbformat import read as load_notebook, NO_CONVERT
from os import environ, symlink
from os.path import relpath, splitext
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from time import time

from .. import __version__
from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    AUTOMATION_VERSION,
    BATCH_ROUTE,
    MODE_NAMES,
    RUN_ROUTE,
    STYLE_ROUTE)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeError)
from ..macros.package import is_equivalent_version
from ..macros.web import format_slug
from .variable import (
    format_text,
    get_data_by_id_from_folder,
    VARIABLE_VIEW_BY_NAME,
    YIELD_DATA_BY_ID_BY_EXTENSION)


class Definition(dict):
    '''
    A definition validates and preserves the original dictionary while adding
    computed attributes.
    '''

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
            validate_imports,
            validate_variables,
            validate_variable_views,
            validate_templates,
            validate_batches,
            validate_datasets,
            validate_scripts,
            validate_environment_variables,
            validate_display_styles,
            validate_display_templates,
            validate_print,
        ]

    def get_variable_definitions(self, mode_name, with_all=False):
        variable_definitions = self.variable_definitions_by_mode_name[
            mode_name]
        if with_all:
            variable_definitions = variable_definitions.copy()
            for MODE_NAME in MODE_NAMES:
                if mode_name == MODE_NAME:
                    continue
                variable_definitions.extend(self.get_variable_definitions(
                    MODE_NAME))
        return variable_definitions

    def get_template_path(self, template_id):
        template_path_by_id = self.template_path_by_id
        if template_id in template_path_by_id:
            template_path = str(self.folder / template_path_by_id[template_id])
        else:
            template_path = f'crosscompute:templates/{template_id}.jinja2'
        return template_path

    def get_template_text(self, mode_name):
        automation_folder = self.folder
        variable_definitions = self.get_variable_definitions(
            mode_name)
        template_definitions = self.template_definitions_by_mode_name[
            mode_name]
        return get_template_text(
            template_definitions, automation_folder, variable_definitions)

    def update_datasets(self):
        automation_folder = self.folder
        for dataset_definition in self.dataset_definitions:
            if 'path' in dataset_definition.reference:
                reference_path = dataset_definition.reference['path']
                source_path = automation_folder / reference_path
                target_path = automation_folder / dataset_definition.path
                if target_path.is_symlink():
                    target_path.unlink()
                elif target_path.exists():
                    continue
                target_folder = target_path.parent
                symlink(source_path.relative_to(target_folder), target_path)


class VariableDefinition(Definition):

    def _initialize(self, kwargs):
        self.mode_name = kwargs['mode_name']
        self._validation_functions = [
            validate_variable_identifiers,
            validate_variable_configuration,
        ]


class TemplateDefinition(Definition):

    def _initialize(self, kwargs):
        self.mode_name = kwargs.get('mode_name')
        self._validation_functions = [
            validate_template_identifiers,
        ]


class BatchDefinition(Definition):

    def _initialize(self, kwargs):
        self.data_by_id = kwargs.get('data_by_id')
        self.is_run = kwargs.get('is_run', False)
        self._validation_functions = [
            validate_batch_identifiers,
            validate_batch_configuration,
        ]


class DatasetDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_dataset_identifiers,
            validate_dataset_configuration,
        ]


class ScriptDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_script_identifiers,
        ]

    def get_command_string(self):
        command_string = self.command
        if command_string:
            return command_string
        if 'path' not in self:
            return
        script_path = self.path
        suffix = script_path.suffix
        if suffix == '.ipynb':
            folder = self.automation_folder / self.folder
            old_path = folder / script_path
            script_path = '.' + str(script_path.with_suffix('.ipynb.py'))
            new_path = folder / script_path
            L.info('exporting %s to %s', self.path, script_path)
            try:
                script_text = PythonExporter().from_notebook_node(
                    load_notebook(old_path, NO_CONVERT))[0]
                with (new_path).open('wt') as script_file:
                    script_file.write(script_text)
            except Exception as e:
                raise CrossComputeConfigurationError(e)
        self.command = command_string = f'python "{script_path}"'
        return command_string


class StyleDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_style_identifiers,
        ]


class PrintDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_print_configuration,
            validate_header_footer_options,
            validate_page_number_options,
        ]


def save_raw_configuration(configuration_path, configuration):
    configuration_format = get_configuration_format(configuration_path)
    save_raw_configuration = {
        'yaml': save_raw_configuration_yaml,
    }[configuration_format]
    return save_raw_configuration(configuration_path, configuration)


def save_raw_configuration_yaml(configuration_path, configuration):
    yaml = YAML()
    try:
        with open(configuration_path, 'wt') as configuration_file:
            yaml.dump(configuration, configuration_file)
    except (OSError, YAMLError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration_path


def load_configuration(configuration_path, index=0):
    configuration_path = Path(configuration_path).absolute()
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
    L.debug('%s loaded', format_path(configuration_path))
    return configuration


def load_raw_configuration(configuration_path, with_comments=False):
    configuration_format = get_configuration_format(configuration_path)
    load_raw_configuration = {
        'ini': load_raw_configuration_ini,
        'toml': load_raw_configuration_toml,
        'yaml': load_raw_configuration_yaml,
    }[configuration_format]
    return load_raw_configuration(configuration_path, with_comments)


def load_raw_configuration_ini(configuration_path, with_comments=False):
    configuration = ConfigParser()
    try:
        paths = configuration.read(configuration_path)
    except (OSError, UnicodeDecodeError) as e:
        raise CrossComputeConfigurationError(e)
    if not paths:
        raise CrossComputeConfigurationError(f'{configuration_path} not found')
    return dict(configuration)


def load_raw_configuration_toml(configuration_path, with_comments=False):
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


def validate_protocol(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute'].strip()
    if not protocol_version:
        raise CrossComputeConfigurationError('crosscompute version required')
    elif not is_equivalent_version(
            protocol_version, __version__, version_depth=3):
        raise CrossComputeConfigurationError(
            f'crosscompute version {protocol_version} is not compatible with '
            f'{__version__}; pip install crosscompute=={protocol_version}')
    return {}


def validate_automation_identifiers(configuration):
    index = configuration.index
    name = configuration.get('name', make_automation_name(index))
    version = configuration.get('version', AUTOMATION_VERSION)
    slug = configuration.get('slug', format_slug(name))
    uri = AUTOMATION_ROUTE.format(automation_slug=slug)
    return {
        'name': name,
        'version': version,
        'slug': slug,
        'uri': uri,
    }


def validate_imports(configuration):
    automation_configurations = []
    remaining_configurations = [configuration]
    while remaining_configurations:
        c = remaining_configurations.pop(0)
        folder = c.folder
        import_configurations = get_dictionaries(c, 'imports')
        for i, import_configuration in enumerate(import_configurations, 1):
            if 'path' in import_configuration:
                path = import_configuration['path']
                try:
                    automation_configuration = load_configuration(
                        folder / path, index=i)
                except CrossComputeConfigurationFormatError as e:
                    raise CrossComputeConfigurationError(e)
            else:
                raise CrossComputeConfigurationError(
                    'path required for each import')
            remaining_configurations.append(automation_configuration)
        automation_configurations.append(c)
    automation_definitions = [
        _ for _ in automation_configurations if 'output' in _]
    assert_unique_values(
        [_.name for _ in automation_definitions],
        'duplicate automation name {{x}}')
    assert_unique_values(
        [_.slug for _ in automation_definitions],
        'duplicate automation slug {{x}}')
    return {
        'automation_definitions': automation_definitions,
    }


def validate_variables(configuration):
    variable_definitions_by_mode_name = {}
    view_names = set()
    for mode_name in MODE_NAMES:
        mode_configuration = get_dictionary(configuration, mode_name)
        variable_definitions = [VariableDefinition(
            _, mode_name=mode_name,
        ) for _ in get_dictionaries(mode_configuration, 'variables')]
        assert_unique_values(
            [_.id for _ in variable_definitions],
            f'duplicate variable id {{x}} in {mode_name}')
        variable_definitions_by_mode_name[mode_name] = variable_definitions
        view_names.update(_.view_name for _ in variable_definitions)
    L.debug('view_names = %s', list(view_names))
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
        environment_variable_ids = get_environment_variable_ids(
            View.environment_variable_definitions)
        if environment_variable_ids:
            L.debug('%s.environment_variable_ids = %s', view_name, list(
                environment_variable_ids))
    return {}


def validate_templates(configuration):
    template_definitions_by_mode_name = {}
    automation_folder = configuration.folder
    for mode_name in MODE_NAMES:
        mode_configuration = get_dictionary(configuration, mode_name)
        template_definitions = [TemplateDefinition(
            _, mode_name=mode_name,
        ) for _ in get_dictionaries(mode_configuration, 'templates')]
        for template_definition in template_definitions:
            template_path = template_definition.path
            if not (automation_folder / template_path).exists():
                raise CrossComputeConfigurationError(
                    f'could not find template {template_path}')
        assert_unique_values(
            [_.id for _ in template_definitions],
            f'duplicate template id {{x}} in {mode_name}')
        template_definitions_by_mode_name[mode_name] = template_definitions
    return {
        'template_definitions_by_mode_name': template_definitions_by_mode_name,
    }


def validate_batches(configuration):
    batch_definitions = []
    raw_batch_definitions = get_dictionaries(configuration, 'batches')
    automation_folder = configuration.folder
    variable_definitions = configuration.get_variable_definitions('input')
    for raw_batch_definition in raw_batch_definitions:
        batch_definitions.extend(get_batch_definitions(
            raw_batch_definition, automation_folder, variable_definitions))
    assert_unique_values(
        [_.folder for _ in batch_definitions],
        'duplicate batch folder {{x}}')
    assert_unique_values(
        [_.name for _ in batch_definitions],
        'duplicate batch name {{x}}')
    assert_unique_values(
        [_.uri for _ in batch_definitions],
        'duplicate batch uri {{x}}')
    return {
        'batch_definitions': batch_definitions,
        'run_definitions': [],
    }


def validate_environment_variables(configuration):
    environment_configuration = get_dictionary(configuration, 'environment')
    environment_variable_definitions = get_dictionaries(
        environment_configuration, 'variables')
    environment_variable_ids = get_environment_variable_ids(
        environment_variable_definitions)
    if environment_variable_ids:
        L.debug('environment_variable_ids = %s', environment_variable_ids)
    return {
        'environment_variable_ids': environment_variable_ids,
    }


def validate_datasets(configuration):
    automation_folder = configuration.folder
    dataset_definitions = [DatasetDefinition(
        _, automation_folder=automation_folder,
    ) for _ in get_dictionaries(configuration, 'datasets')]
    return {
        'dataset_definitions': dataset_definitions,
    }


def validate_scripts(configuration):
    automation_folder = configuration.folder
    script_definitions = [ScriptDefinition(
        _, automation_folder=automation_folder,
    ) for _ in get_dictionaries(configuration, 'scripts')]
    return {
        'script_definitions': script_definitions,
    }


def validate_display_styles(configuration):
    display_dictionary = get_dictionary(configuration, 'display')
    automation_folder = configuration.folder
    automation_index = configuration.index
    automation_uri = configuration.uri
    reference_time = time()
    style_definitions = []
    for raw_style_definition in get_dictionaries(
            display_dictionary, 'styles'):
        style_definition = StyleDefinition(raw_style_definition)
        style_uri = style_definition.uri
        style_path = style_definition.path
        if '//' not in style_uri:
            path = automation_folder / style_path
            if not path.exists():
                raise CrossComputeConfigurationError(
                    f'{path} not found for style')
            style_name = format_slug(
                f'{splitext(style_path)[0]}-{reference_time}')
            style_uri = STYLE_ROUTE.format(style_name=style_name)
            if automation_index > 0:
                style_uri = automation_uri + style_uri
            style_definition.path = style_path
            style_definition.uri = style_uri
        style_definitions.append(style_definition)
    css_uris = [_.uri for _ in style_definitions]
    return {
        'style_definitions': style_definitions,
        'css_uris': css_uris,
    }


def validate_display_templates(configuration):
    display_dictionary = get_dictionary(configuration, 'display')
    template_path_by_id = {}
    for raw_template_definition in get_dictionaries(
            display_dictionary, 'templates'):
        template_definition = TemplateDefinition(raw_template_definition)
        template_id = template_definition.id
        template_path_by_id[template_id] = template_definition.path
    return {
        'template_path_by_id': template_path_by_id,
    }


def validate_print(configuration):
    print_dictionary = get_dictionary(configuration, 'print')
    return {
        'print_definition': PrintDefinition(print_dictionary),
    }


def validate_template_identifiers(template_definition):
    try:
        template_path = template_definition['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each template')
    template_id = template_definition.get('id', template_path)
    return {
        'id': template_id,
        'path': Path(template_path),
    }


def validate_variable_identifiers(variable_definition):
    # TODO: Check that variable_id does not have quotes
    try:
        variable_id = variable_definition['id']
        view_name = variable_definition['view']
        variable_path = variable_definition['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each variable')
    if relpath(variable_path).startswith('..'):
        raise CrossComputeConfigurationError(
            f'path {variable_path} for variable {variable_id} must be within '
            'the folder')
    return {
        'id': variable_id,
        'view_name': view_name,
        'path': Path(variable_path),
    }


def validate_variable_configuration(variable_definition):
    variable_configuration = get_dictionary(
        variable_definition, 'configuration')
    return {
        'configuration': variable_configuration,
    }


def validate_batch_identifiers(batch_definition):
    is_run = batch_definition.is_run
    try:
        folder = Path(get_scalar_text(batch_definition, 'folder'))
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each batch')
    name = get_scalar_text(batch_definition, 'name', folder.name)
    slug = get_scalar_text(batch_definition, 'slug', name)
    data_by_id = batch_definition.data_by_id
    if data_by_id and not is_run:
        try:
            folder = format_text(str(folder), data_by_id)
            name = format_text(name, data_by_id)
            slug = format_text(slug, data_by_id)
        except CrossComputeConfigurationError as e:
            batch_configuration = batch_definition.get('configuration', {})
            if 'path' in batch_configuration:
                e.path = batch_configuration['path']
            raise
    d = {'folder': folder, 'name': name, 'slug': slug}
    if data_by_id:
        for k, v in d.items():
            if k in batch_definition:
                batch_definition[k] = v
    if data_by_id is not None:
        if is_run:
            uri = RUN_ROUTE.format(run_slug=slug)
        else:
            slug = format_slug(slug)
            uri = BATCH_ROUTE.format(batch_slug=slug)
        d.update({'slug': slug, 'uri': uri})
    return d


def validate_batch_configuration(batch_definition):
    batch_reference = get_dictionary(batch_definition, 'reference')
    batch_configuration = get_dictionary(batch_definition, 'configuration')
    return {
        'reference': batch_reference,
        'configuration': batch_configuration,
    }


def validate_dataset_identifiers(dataset_definition):
    path = Path(dataset_definition.get('path', '').strip())
    return {
        'path': path,
    }


def validate_dataset_configuration(dataset_definition):
    automation_folder = dataset_definition.automation_folder
    dataset_reference = get_dictionary(dataset_definition, 'reference')
    if 'path' in dataset_reference:
        source_path = Path(dataset_reference['path'].strip())
        if not (automation_folder / source_path).exists():
            raise CrossComputeConfigurationError(
                f'could not find dataset reference path {source_path}')
        target_path = dataset_definition.path
        if target_path.exists() and not target_path.is_symlink():
            raise CrossComputeConfigurationError(
                'refusing to overwrite existing dataset; please delete '
                f'{target_path} from the disk as defined')
    return {
        'reference': dataset_reference,
    }


def validate_script_identifiers(script_definition):
    folder = script_definition.get('folder', '.').strip()

    if 'path' in script_definition:
        path = Path(script_definition['path'].strip())
        suffix = path.suffix
        if suffix not in ['.ipynb', '.py']:
            raise CrossComputeConfigurationError(
                f'{suffix} not supported for script path')
    else:
        path = None

    if 'command' in script_definition:
        command = script_definition['command'].strip()
    else:
        command = None

    return {
        'folder': Path(folder),
        'path': path,
        'command': command,
    }


def validate_style_identifiers(style_definition):
    uri = style_definition.get('uri', '').strip()
    path = style_definition.get('path', '').strip()
    if not uri and not path:
        raise CrossComputeConfigurationError(
            'uri or path required for each style')
    return {
        'uri': uri,
        'path': Path(path),
    }


def validate_print_configuration(print_dictionary):
    print_configuration = get_dictionary(
        print_dictionary, 'configuration')
    return {
        'configuration': print_configuration,
    }


def validate_header_footer_options(print_dictionary):
    print_configuration = print_dictionary.configuration
    key = 'header-footer'
    options = get_dictionary(print_configuration, key)
    options['skip-first'] = bool(options.get('skip-first'))
    return {}


def validate_page_number_options(print_dictionary):
    print_configuration = print_dictionary.configuration
    key = 'page-number'
    options = get_dictionary(print_configuration, key)
    location = options.get('location')
    if location and location not in ['header', 'footer']:
        raise CrossComputeConfigurationError(
            f'{location} location not supported for {key}')
    alignment = options.get('alignment')
    if alignment and alignment not in ['left', 'center', 'right']:
        raise CrossComputeConfigurationError(
            f'{alignment} alignment not supported for {key}')
    return {}


def get_configuration_format(path):
    file_extension = path.suffix
    try:
        configuration_format = {
            '.cfg': 'ini',
            '.ini': 'ini',
            '.toml': 'toml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }[file_extension]
    except KeyError:
        raise CrossComputeConfigurationFormatError((
            f'{file_extension} format not supported for automation '
            'configuration').lstrip())
    return configuration_format


def get_template_text(
        template_definitions, automation_folder, variable_definitions):
    template_texts = []
    for template_definition in template_definitions:
        path = automation_folder / template_definition.path
        with open(path, 'rt') as f:
            template_text = f.read().strip()
        if not template_text:
            continue
        template_texts.append(template_text)
    if not template_texts:
        variable_ids = [_.id for _ in variable_definitions]
        template_texts = ['\n'.join('{%s}' % _ for _ in variable_ids)]
    return '\n'.join(template_texts)


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
                f'{variable_id} is missing in the environment as defined')
        variable_ids.add(variable_id)
    return variable_ids


def get_scalar_text(d, key, default=None):
    value = d.get(key) or default
    if value is None:
        raise KeyError(key)
    if isinstance(value, dict):
        raise CrossComputeConfigurationError(
            f'surround {key} with quotes since it begins with a {{')
    return value


def get_batch_definitions(
        raw_batch_definition, automation_folder, variable_definitions):
    batch_definitions = []
    raw_batch_definition = BatchDefinition(raw_batch_definition)
    reference = raw_batch_definition.reference
    batch_configuration = raw_batch_definition.configuration

    if 'folder' in reference:
        reference_folder = reference['folder']
        reference_data_by_id = get_data_by_id_from_folder(
            automation_folder / reference_folder / 'input',
            variable_definitions)
    else:
        reference_data_by_id = {}

    if 'path' in batch_configuration:
        batch_configuration_path = Path(batch_configuration['path'])
        file_extension = batch_configuration_path.suffix
        try:
            yield_data_by_id = YIELD_DATA_BY_ID_BY_EXTENSION[file_extension]
        except KeyError:
            raise CrossComputeConfigurationError((
                f'{file_extension} format not supported for batch '
                'configuration').lstrip())
        for configuration_data_by_id in yield_data_by_id(
                automation_folder / batch_configuration_path,
                variable_definitions):
            data_by_id = reference_data_by_id | configuration_data_by_id
            batch_definitions.append(BatchDefinition(
                raw_batch_definition, data_by_id=data_by_id))
    else:
        batch_definitions.append(BatchDefinition(
            raw_batch_definition, data_by_id=reference_data_by_id))

    return batch_definitions


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


def assert_unique_values(xs, message):
    for x, count in Counter(xs).items():
        if count > 1:
            raise CrossComputeConfigurationError(message.format(x=x))


L = getLogger(__name__)

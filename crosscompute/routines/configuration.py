# TODO: Save to ini, toml
import json
import shutil
from collections import Counter
from configparser import ConfigParser
from datetime import timedelta
from logging import getLogger
from os import environ
from os.path import basename, relpath, splitext
from pathlib import Path
from string import Template
from time import time

import tomli
from invisibleroads_macros_log import format_path
from invisibleroads_macros_text import format_slug
from nbconvert import PythonExporter
from nbformat import read as load_notebook, NO_CONVERT
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .. import __version__
from ..constants import (
    Status,
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    AUTOMATION_VERSION,
    BATCH_ROUTE,
    BUTTON_TEXT_BY_ID,
    DEBUG_VARIABLE_DICTIONARIES,
    DESIGN_NAMES_BY_PAGE_ID,
    INTERVAL_UNIT_NAMES,
    PACKAGE_MANAGER_NAMES,
    PRINTER_BY_NAME,
    STEP_NAMES,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VIEW_BY_NAME)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotImplementedError,
    CrossComputeError)
from ..macros.iterable import find_item
from ..macros.package import is_equivalent_version
from .printer import initialize_printer_by_name
from .variable import (
    format_text,
    get_data_by_id_from_folder,
    initialize_view_by_name,
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
        self.group_definitions = kwargs['group_definitions']
        self._validation_functions = [
            validate_protocol,
            validate_automation_identifiers,
            validate_authorization,  # Must run before validate_imports
            validate_imports,
            validate_variables,
            validate_variable_views,
            validate_templates,
            validate_batches,
            validate_datasets,
            validate_scripts,
            validate_environment,
            validate_display_styles,
            validate_display_templates,
            validate_display_pages,
            validate_display_buttons,
            validate_prints]

    def get_variable_definitions(self, step_name, with_all=False):
        variable_definitions = self.variable_definitions_by_step_name.get(
            step_name, [])
        if with_all:
            variable_definitions = variable_definitions.copy()
            for STEP_NAME in STEP_NAMES:
                if step_name == STEP_NAME:
                    continue
                variable_definitions.extend(self.get_variable_definitions(
                    STEP_NAME))
        return variable_definitions

    def get_template_text(self, step_name):
        automation_folder = self.folder
        variable_definitions = self.get_variable_definitions(step_name)
        template_definitions = self.template_definitions_by_step_name[
            step_name]
        return get_template_text(
            template_definitions, automation_folder, variable_definitions)

    def get_design_name(self, page_id):
        design_name = DESIGN_NAMES_BY_PAGE_ID[page_id][0]
        if page_id in self.page_definition_by_id:
            page_definition = self.page_definition_by_id[page_id]
            design_name = page_definition.configuration.get(
                'design', design_name)
        elif page_id in STEP_NAMES:
            variable_definitions = self.get_variable_definitions(page_id)
            if not variable_definitions:
                design_name = 'none'
        return design_name

    def get_button_text(self, button_id):
        button_text = BUTTON_TEXT_BY_ID[button_id]
        button_definition_by_id = self.button_definition_by_id
        if button_id in button_definition_by_id:
            button_definition = button_definition_by_id[button_id]
            button_configuration = button_definition.configuration
            button_text = button_configuration.get('button-text', button_text)
        return button_text


class VariableDefinition(Definition):

    def _initialize(self, kwargs):
        self.step_name = kwargs['step_name']
        self._validation_functions = [
            validate_variable_identifiers,
            validate_variable_configuration]


class TemplateDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self.step_name = kwargs.get('step_name')
        self._validation_functions = [
            validate_template_identifiers]


class BatchDefinition(Definition):

    def _initialize(self, kwargs):
        self.data_by_id = kwargs.get('data_by_id')
        self.is_run = kwargs.get('is_run', False)
        self._validation_functions = [
            validate_batch_identifiers,
            validate_batch_configuration]

    def get_status(self):
        status = Status.NEW
        path = self.folder / 'debug' / 'variables.dictionary'
        if path.exists():
            d = json.load(path.open('rt'))
            return_code = d['return_code']
            status = Status.DONE if return_code == 0 else Status.FAILED
        return status


class DatasetDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_dataset_identifiers,
            validate_dataset_reference]


class ScriptDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_script_identifiers]

    def get_command_string(self):
        command_string = self.command
        if command_string:
            return command_string
        folder = self.automation_folder / self.folder
        if 'path' in self:
            script_path = self.path
            suffix = script_path.suffix
            if suffix == '.ipynb':
                old_path = folder / script_path
                script_path = '.' + str(script_path.with_suffix('.ipynb.py'))
                new_path = folder / script_path
                L.info(
                    'exporting %s to %s in %s', self.path, script_path, folder)
                try:
                    script_text = PythonExporter().from_notebook_node(
                        load_notebook(old_path, NO_CONVERT))[0]
                    with new_path.open('wt') as script_file:
                        script_file.write(script_text)
                except Exception as e:
                    raise CrossComputeConfigurationError(e)
        elif 'function' in self:
            script_path = '.run.py'
            new_path = folder / script_path
            function_string = self['function']
            with new_path.open('wt') as f:
                f.write(RUN_PY.substitute({
                    'module_name': function_string.split('.')[0],
                    'function_string': function_string}))
        else:
            return
        self.command = command_string = f'python3 "{script_path}"'
        return command_string


class PackageDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_package_identifiers]


class PortDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_port_identifiers]


class StyleDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_style_identifiers]


class PageDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_page_identifiers,
            validate_page_configuration]


class ButtonDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_button_identifiers,
            validate_button_configuration]


class TokenDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_token_identifiers]


class GroupDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_group_identifiers]


class PermissionDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_permission_identifiers]


class PrintDefinition(Definition):

    def _initialize(self, kwargs):
        self._validation_functions = [
            validate_print_identifiers,
            validate_print_configuration,
            validate_header_footer_options,
            validate_page_number_options]


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


def load_configuration(configuration_path, index=0, group_definitions=[]):
    configuration_path = Path(configuration_path).absolute()
    configuration = load_raw_configuration(configuration_path)
    try:
        configuration = AutomationDefinition(
            configuration,
            path=configuration_path,
            index=index,
            group_definitions=group_definitions)
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
    description = configuration.get('description', '')
    version = configuration.get('version', AUTOMATION_VERSION)
    slug = configuration.get('slug', format_slug(name))
    uri = AUTOMATION_ROUTE.format(automation_slug=slug)
    return {
        'name': name,
        'description': description,
        'version': version,
        'slug': slug,
        'uri': uri}


def validate_imports(configuration):
    automation_configurations = [configuration]
    folder = configuration.folder
    group_definitions = getattr(configuration, 'group_definitions', [])
    import_configurations = get_dictionaries(configuration, 'imports')
    for i, import_configuration in enumerate(import_configurations.copy(), 1):
        if 'path' in import_configuration:
            path = folder / import_configuration['path']
            try:
                automation_configuration = load_configuration(
                    path, index=i, group_definitions=group_definitions)
            except CrossComputeConfigurationFormatError as e:
                raise CrossComputeConfigurationError(e)
            import_configuration['path'] = path
        else:
            raise CrossComputeConfigurationError(
                'path required for each import')
        import_configurations.extend(
            automation_configuration.import_configurations)
        automation_configurations.extend(
            automation_configuration.automation_definitions)
    automation_definitions = [
        _ for _ in automation_configurations if 'output' in _]
    assert_unique_values([
        _.name for _ in automation_definitions], 'duplicate name {x}')
    assert_unique_values([
        _.slug for _ in automation_definitions], 'duplicate slug {x}')
    return {
        'import_configurations': import_configurations,
        'automation_definitions': automation_definitions}


def validate_variables(configuration):
    variable_definitions_by_step_name = {}
    view_names = set()
    for step_name in STEP_NAMES:
        step_configuration = get_dictionary(configuration, step_name)
        variable_dictionaries = get_dictionaries(
            step_configuration, 'variables')
        if step_name == 'debug':
            variable_dictionaries[:0] = DEBUG_VARIABLE_DICTIONARIES
        variable_definitions = [VariableDefinition(
            _, step_name=step_name) for _ in variable_dictionaries]
        assert_unique_values([
            _.id for _ in variable_definitions
        ], f'duplicate variable id {{x}} in {step_name}')
        variable_definitions_by_step_name[step_name] = variable_definitions
        view_names.update(_.view_name for _ in variable_definitions)
    L.debug('view_names = %s', list(view_names))
    return {
        'variable_definitions_by_step_name': variable_definitions_by_step_name,
        '___view_names': view_names}


def validate_variable_views(configuration):
    # TODO: Validate variable view configurations
    initialize_view_by_name()
    for view_name in configuration.___view_names:
        try:
            View = VIEW_BY_NAME[view_name]
        except KeyError:
            raise CrossComputeConfigurationError(f'{view_name} not installed')
        environment_variable_ids = get_environment_variable_ids(
            View.environment_variable_definitions)
        if environment_variable_ids:
            L.debug('%s.environment_variable_ids = %s', view_name, list(
                environment_variable_ids))
    return {}


def validate_templates(configuration):
    template_definitions_by_step_name = {}
    automation_folder = configuration.folder
    for step_name in STEP_NAMES:
        step_configuration = get_dictionary(configuration, step_name)
        template_definitions = [TemplateDefinition(
            _, automation_folder=automation_folder, step_name=step_name,
        ) for _ in get_dictionaries(step_configuration, 'templates')]
        assert_unique_values([
            _.id for _ in template_definitions],
            f'duplicate template id {{x}} in {step_name}')
        template_definitions_by_step_name[step_name] = template_definitions
    return {
        'template_definitions_by_step_name': template_definitions_by_step_name}


def validate_batches(configuration):
    batch_definitions = []
    raw_batch_definitions = get_dictionaries(configuration, 'batches')
    automation_folder = configuration.folder
    variable_definitions = configuration.get_variable_definitions('input')
    for raw_batch_definition in raw_batch_definitions:
        batch_definitions.extend(get_batch_definitions(
            raw_batch_definition, automation_folder, variable_definitions))
    if 'output' in configuration and not batch_definitions:
        raise CrossComputeConfigurationError(
            'no batches configured; please define at least one batch')
    assert_unique_values([
        _.folder for _ in batch_definitions], 'duplicate batch folder {x}')
    assert_unique_values([
        _.name for _ in batch_definitions], 'duplicate batch name {x}')
    assert_unique_values([
        _.uri for _ in batch_definitions], 'duplicate batch uri {x}')
    return {'batch_definitions': batch_definitions}


def validate_environment(configuration):
    d = get_dictionary(configuration, 'environment')
    port_definitions = get_port_definitions(
        d, configuration.get_variable_definitions('log')
        + configuration.get_variable_definitions('debug'))
    environment_variable_ids = get_environment_variable_ids(get_dictionaries(
        d, 'variables'))
    batch_concurrency_name = d.get('batch', 'process').lower()
    if batch_concurrency_name not in ('process', 'thread', 'single'):
        raise CrossComputeConfigurationError(
            f'"{batch_concurrency_name}" batch concurrency is not supported')
    interval_text = d.get('interval', '').strip()
    interval_timedelta = get_interval_timedelta(interval_text)
    return {
        'engine_name': get_engine_name(d),
        'parent_image_name': d.get('image', 'python').strip(),
        'package_definitions': [PackageDefinition(_) for _ in get_dictionaries(
            d, 'packages')],
        'port_definitions': port_definitions,
        'environment_variable_ids': environment_variable_ids,
        'batch_concurrency_name': batch_concurrency_name,
        'interval_timedelta': interval_timedelta}


def validate_datasets(configuration):
    automation_folder = configuration.folder
    dataset_definitions = [DatasetDefinition(
        _, automation_folder=automation_folder,
    ) for _ in get_dictionaries(configuration, 'datasets')]
    return {'dataset_definitions': dataset_definitions}


def validate_scripts(configuration):
    automation_folder = configuration.folder
    script_definitions = [ScriptDefinition(
        _, automation_folder=automation_folder,
    ) for _ in get_dictionaries(configuration, 'scripts')]
    return {'script_definitions': script_definitions}


def validate_display_styles(configuration):
    display_dictionary = get_dictionary(configuration, 'display')
    automation_folder = configuration.folder
    automation_index = configuration.index
    automation_uri = configuration.uri
    reference_time = time()
    style_definitions = []
    for raw_style_definition in get_dictionaries(display_dictionary, 'styles'):
        style_definition = StyleDefinition(raw_style_definition)
        style_uri = style_definition.uri
        if '//' not in style_uri:
            style_path = style_definition.path
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
    return {
        'style_definitions': style_definitions,
        'css_uris': [_.uri for _ in style_definitions]}


def validate_display_templates(configuration):
    template_path_by_id = {}
    display_dictionary = get_dictionary(configuration, 'display')
    automation_folder = configuration.folder
    for raw_template_definition in get_dictionaries(
            display_dictionary, 'templates'):
        template_definition = TemplateDefinition(
            raw_template_definition, automation_folder=automation_folder)
        template_id = template_definition.id
        template_path_by_id[template_id] = template_definition.path
    return {'template_path_by_id': template_path_by_id}


def validate_display_pages(configuration):
    display_dictionary = get_dictionary(configuration, 'display')
    page_definitions = [PageDefinition(_) for _ in get_dictionaries(
        display_dictionary, 'pages')]
    page_definition_by_id = {_.id: _ for _ in page_definitions}
    return {'page_definition_by_id': page_definition_by_id}


def validate_display_buttons(configuration):
    display_dictionary = get_dictionary(configuration, 'display')
    button_definitions = [ButtonDefinition(_) for _ in get_dictionaries(
        display_dictionary, 'buttons')]
    button_definition_by_id = {_.id: _ for _ in button_definitions}
    return {'button_definition_by_id': button_definition_by_id}


def validate_authorization(configuration):
    authorization_dictionary = get_dictionary(configuration, 'authorization')
    token_definitions = [TokenDefinition(
        _, automation_folder=configuration.folder,
    ) for _ in get_dictionaries(authorization_dictionary, 'tokens')]
    identities_by_token = {
        token: identities for _ in token_definitions
        for token, identities in _.identities_by_token.items()}
    parent_group_definitions = getattr(configuration, 'group_definitions', [])
    child_group_definitions = [GroupDefinition(_) for _ in get_dictionaries(
        authorization_dictionary, 'groups')]
    group_definitions = child_group_definitions + parent_group_definitions
    return {
        'identities_by_token': identities_by_token,
        'group_definitions': group_definitions}


def validate_prints(configuration):
    print_definitions = [PrintDefinition(_) for _ in get_dictionaries(
        configuration, 'prints')]
    return {'print_definitions': print_definitions}


def validate_template_identifiers(template_dictionary):
    try:
        template_path = template_dictionary['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each template')
    automation_folder = template_dictionary.automation_folder
    template_path = Path(template_path)
    if not (automation_folder / template_path).exists():
        raise CrossComputeConfigurationError(
            f'could not find template {template_path}')
    return {
        'id': template_dictionary.get('id', template_path.stem),
        'path': template_path}


def validate_variable_identifiers(variable_dictionary):
    try:
        variable_id = variable_dictionary['id']
        view_name = variable_dictionary['view']
        variable_path = variable_dictionary['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each variable')
    if not VARIABLE_ID_PATTERN.match(variable_id):
        raise CrossComputeConfigurationError(
            f'{variable_id} is not a valid variable id; please use only '
            'lowercase, uppercase, numbers, hyphens, underscores and spaces')
    if relpath(variable_path).startswith('..'):
        raise CrossComputeConfigurationError(
            f'path {variable_path} for variable {variable_id} must be within '
            'the folder')
    return {
        'id': variable_id,
        'view_name': view_name,
        'path': Path(variable_path)}


def validate_variable_configuration(variable_dictionary):
    variable_configuration = get_dictionary(
        variable_dictionary, 'configuration')
    return {'configuration': variable_configuration}


def validate_batch_identifiers(batch_dictionary):
    is_run = batch_dictionary.is_run
    try:
        folder = get_scalar_text(batch_dictionary, 'folder')
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each batch')
    name = get_scalar_text(batch_dictionary, 'name', basename(folder))
    slug = get_scalar_text(batch_dictionary, 'slug', name)
    data_by_id = batch_dictionary.data_by_id
    if data_by_id and not is_run:
        try:
            folder = format_text(folder, data_by_id)
            name = format_text(name, data_by_id)
            slug = format_text(slug, data_by_id)
        except CrossComputeConfigurationNotImplementedError:
            raise
        except CrossComputeConfigurationError as e:
            batch_configuration = get_dictionary(
                batch_dictionary, 'configuration')
            if 'path' in batch_configuration:
                e.path = batch_configuration['path']
            raise
    d = {'folder': Path(folder), 'name': name, 'slug': slug}
    if data_by_id:
        for k, v in d.items():
            if k in batch_dictionary:
                batch_dictionary[k] = v
    if data_by_id is not None:
        if not is_run:
            slug = format_slug(slug)
        uri = BATCH_ROUTE.format(batch_slug=slug)
        d.update({'slug': slug, 'uri': uri})
    return d


def validate_batch_configuration(batch_dictionary):
    batch_reference = get_dictionary(batch_dictionary, 'reference')
    batch_configuration = get_dictionary(batch_dictionary, 'configuration')
    return {
        'reference': batch_reference,
        'configuration': batch_configuration}


def validate_dataset_identifiers(dataset_dictionary):
    return {'path': get_folder_plus_path(dataset_dictionary)}


def validate_dataset_reference(dataset_dictionary):
    automation_folder = dataset_dictionary.automation_folder
    dataset_reference = get_dictionary(dataset_dictionary, 'reference')
    reference_path = get_folder_plus_path(dataset_reference)
    if reference_path:
        source_path = automation_folder / reference_path
        if not source_path.exists():
            if source_path.is_symlink():
                raise CrossComputeConfigurationError(
                    f'invalid symlink for dataset reference {reference_path}')
            elif source_path.name == 'runs':
                source_path.mkdir(parents=True)
            else:
                raise CrossComputeConfigurationError(
                    f'could not find dataset reference {reference_path}')
        target_path = dataset_dictionary.path
        if target_path.exists() and not target_path.is_symlink():
            raise CrossComputeConfigurationError(
                'refusing to overwrite existing dataset; please delete '
                f'{target_path} from the disk as defined')
    return {'reference': dataset_reference}


def validate_script_identifiers(script_dictionary):
    folder = script_dictionary.get('folder', '.').strip()

    if 'path' in script_dictionary:
        path = Path(script_dictionary['path'].strip())
        suffix = path.suffix
        if suffix not in ['.ipynb', '.py']:
            raise CrossComputeConfigurationError(
                f'{suffix} not supported for script path')
    else:
        path = None

    if 'command' in script_dictionary:
        command = script_dictionary['command'].strip()
    else:
        command = None

    return {
        'folder': Path(folder),
        'path': path,
        'command': command}


def validate_package_identifiers(package_dictionary):
    try:
        package_id = package_dictionary['id']
        manager_name = package_dictionary['manager']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each package')
    if manager_name not in PACKAGE_MANAGER_NAMES:
        raise CrossComputeConfigurationError(
            f'"{manager_name}" manager is not supported')
    return {
        'id': package_id,
        'manager_name': manager_name}


def validate_port_identifiers(port_dictionary):
    try:
        port_id = port_dictionary['id']
        port_number = port_dictionary['number']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each port')
    try:
        port_number = int(port_number)
    except ValueError:
        raise CrossComputeConfigurationError(
            f'{port_number} must be an integer')
    return {
        'id': port_id,
        'number': port_number}


def validate_style_identifiers(style_dictionary):
    uri = style_dictionary.get('uri', '').strip()
    path = style_dictionary.get('path', '').strip()
    if not uri and not path:
        raise CrossComputeConfigurationError(
            'uri or path required for each style')
    return {'uri': uri, 'path': Path(path)}


def validate_page_identifiers(page_dictionary):
    try:
        page_id = page_dictionary['id']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each page')
    if page_id not in DESIGN_NAMES_BY_PAGE_ID:
        raise CrossComputeConfigurationError(
            f'{page_id} page not supported for page configuration')
    return {'id': page_id}


def validate_page_configuration(page_dictionary):
    page_configuration = get_dictionary(page_dictionary, 'configuration')
    page_id = page_dictionary['id']
    design_name = page_configuration.get('design')
    design_names = DESIGN_NAMES_BY_PAGE_ID[page_id]
    if design_name not in design_names:
        raise CrossComputeConfigurationError(
            f'"{design_name}" design not supported for {page_id} page')
    return {'configuration': page_configuration}


def validate_button_identifiers(button_dictionary):
    try:
        button_id = button_dictionary['id']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each button')
    if button_id not in BUTTON_TEXT_BY_ID:
        raise CrossComputeConfigurationError(
            f'{button_id} button not supported for button configuration')
    return {'id': button_id}


def validate_button_configuration(button_dictionary):
    button_configuration = get_dictionary(button_dictionary, 'configuration')
    return {'configuration': button_configuration}


def validate_token_identifiers(token_dictionary):
    try:
        token_path = token_dictionary['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each token')
    path = Path(token_dictionary.automation_folder, token_path)
    suffix = path.suffix
    if suffix == '.yml':
        d = load_raw_configuration_yaml(path)
    else:
        raise CrossComputeConfigurationError(
            f'{suffix} not supported for token paths')
    identities_by_token = {}
    for token, identities in d.items():
        token = str(token)
        variable_match = VARIABLE_ID_TEMPLATE_PATTERN.match(token)
        if variable_match:
            variable_id = variable_match.group(1)
            try:
                token = environ[variable_id]
            except KeyError:
                e = CrossComputeConfigurationError(
                    f'{variable_id} is missing in the environment')
                e.path = path
                raise e
        identities_by_token[token] = identities
    return {'identities_by_token': identities_by_token}


def validate_group_identifiers(group_dictionary):
    try:
        group_configuration = group_dictionary['configuration']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} required for each group')
    group_permissions = [PermissionDefinition(_) for _ in get_dictionaries(
        group_dictionary, 'permissions')]
    return {
        'configuration': group_configuration or {},
        'permissions': group_permissions}


def validate_permission_identifiers(permission_dictionary):
    try:
        permission_id = permission_dictionary['id']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} required for each permission')
    if permission_id not in PERMISSION_IDS:
        raise CrossComputeConfigurationError(
            f'"{permission_id}" permission not supported')
    permission_action = permission_dictionary.get('action', 'accept')
    if permission_action not in PERMISSION_ACTIONS:
        raise CrossComputeConfigurationError(
            f'"{permission_action}" action not supported')
    return {'id': permission_id, 'action': permission_action}


def validate_print_identifiers(print_dictionary):
    initialize_printer_by_name()
    print_format = print_dictionary.get('format', '').strip()
    if print_format:
        try:
            PRINTER_BY_NAME[print_format]
        except KeyError:
            printer_names = PRINTER_BY_NAME.keys()
            if printer_names:
                extra_message = 'try ' + ' '.join(printer_names)
            else:
                extra_message = 'install crosscompute-printers-pdf'
            raise CrossComputeConfigurationError(
                f'{print_format} is not a supported printer; {extra_message}')
    print_folder = Path(print_dictionary.get('folder', '')).expanduser()
    print_name = print_dictionary.get('name', '')
    return {
        'format': print_format,
        'folder': print_folder,
        'name': print_name}


def validate_print_configuration(print_dictionary):
    print_configuration = get_dictionary(
        print_dictionary, 'configuration')
    return {'configuration': print_configuration}


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


def get_engine_name(environment_dictionary):
    engine_name = environment_dictionary.get('engine', 'unsafe').strip()
    if engine_name == 'podman':
        if not shutil.which('podman'):
            L.warning('podman is not available on this machine')
    elif engine_name == 'unsafe':
        L.warning(
            'using engine=unsafe; use engine=podman for untrusted code')
    else:
        raise CrossComputeConfigurationError(
            f'"{engine_name}" engine is not supported')
    return engine_name


def get_port_definitions(environment_dictionary, variable_definitions):
    port_definitions = [PortDefinition(_) for _ in get_dictionaries(
        environment_dictionary, 'ports')]
    for port_definition in port_definitions:
        port_id = port_definition.id
        try:
            variable_definition = find_item(
                variable_definitions, 'id', port_id)
        except StopIteration:
            raise CrossComputeConfigurationError(
                f'{port_id} port must have a matching variable definition')
        step_name = variable_definition.step_name
        if step_name not in ['log', 'debug']:
            raise CrossComputeConfigurationError(
                f'{port_id} port must correspond to a log or debug variable')
        port_definition.step_name = step_name
    return port_definitions


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


def get_interval_timedelta(interval_text):
    if not interval_text:
        return
    try:
        count, name = interval_text.split()
        count = int(count)
    except ValueError:
        raise CrossComputeConfigurationError(
            f'unparseable interval "{interval_text}"; '
            f'expected something like "30 minutes"')
    for unit_name in INTERVAL_UNIT_NAMES:
        if name.startswith(unit_name[:-1]):
            break
    else:
        unit_names_text = ' '.join(INTERVAL_UNIT_NAMES)
        raise CrossComputeConfigurationError(
            f'unsupported interval unit "{name}" in "{interval_text}"; '
            f'expected {unit_names_text}')
    return timedelta(**{unit_name: count})


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


def get_folder_plus_path(d):
    folder = d.get('folder', '').strip()
    path = d.get('path', '').strip()
    if not folder and not path:
        return
    return Path(folder, path)


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


RUN_PY = Template('''\
import inspect
from os import getenv
from pathlib import Path

import $module_name


folder_by_name = {}
for x in 'input_folder', 'output_folder', 'log_folder', 'debug_folder':
    folder_by_name[x] = Path(getenv('CROSSCOMPUTE_' + x.upper()))
d = {}
for x in inspect.getargspec($function_string).args:
    d[x] = folder_by_name[x]
$function_string(**d)''')


PERMISSION_IDS = [
    'add_token',
    'see_root',
    'see_automation',
    'see_batch',
    'run_automation',
]
PERMISSION_ACTIONS = [
    'accept',
    'match',
]


L = getLogger(__name__)

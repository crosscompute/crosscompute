import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from os import environ
from os.path import relpath, splitext
from time import time

from invisibleroads_macros_text import format_name
from invisibleroads_macros_web.markdown import (
    get_html_from_markdown,
    remove_single_paragraph)
from nbformat import read as load_notebook, NO_CONVERT

from .. import __version__
from ..constants import (
    Status,
    ATTRIBUTION_TEXT,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    BUTTON_TEXT_BY_ID,
    COPYRIGHT_NAME,
    COPYRIGHT_URI,
    COPYRIGHT_YEAR,
    DEBUG_VARIABLE_DICTIONARIES,
    DESIGN_NAMES_BY_PAGE_ID,
    INTERVAL_UNIT_NAMES,
    PACKAGE_MANAGER_NAMES,
    PRINTER_NAMES,
    STEP_NAMES,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_ID_TEMPLATE_PATTERN)
from ..exceptions import (
    CrossComputeError)
from ..macros.iterable import find_item
from ..macros.package import is_equivalent_version
from ..settings import (
    printer_by_name,
    view_by_name)
from .log import Clock
from .printer import (
    initialize_printer_by_name)
from .variable import (
    initialize_view_by_name,
    load_file_json)


class AutomationDefinition(Definition):

    def _initialize(self, kwargs):
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
            validate_display_buttons]

    def get_variable_definitions(self, step_name, with_all=False):
        if with_all:
            variable_definitions = variable_definitions.copy()
            for STEP_NAME in STEP_NAMES:
                if step_name == STEP_NAME:
                    continue
                variable_definitions.extend(self.get_variable_definitions(
                    STEP_NAME))
        return variable_definitions

    def is_interval_ready(self, batch_definition):
        interval_timedelta = self.interval_timedelta
        if interval_timedelta:
            run_datetime = datetime.fromtimestamp(
                batch_definition.clock.get_end_time('run'))
            if datetime.now() > run_datetime + interval_timedelta:
                return True
        return False


class VariableDefinition(Definition):

    def _initialize(self, kwargs):
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

    def get_status(self):
        status = Status.NEW
        path = self.folder / 'debug' / 'variables.dictionary'
        if path.exists():
            d = load_file_json(path)
            return_code = d['return_code']
            status = Status.DONE if return_code == 0 else Status.FAILED
        return status


class DatasetDefinition(Definition):

    def _initialize(self, kwargs):
        self.automation_folder = kwargs['automation_folder']
        self._validation_functions = [
            validate_dataset_identifiers,
            validate_dataset_reference]


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


def save_raw_configuration(configuration_path, configuration):
    configuration_format = get_configuration_format(configuration_path)
    save_raw_configuration = {
        'yaml': save_raw_configuration_yaml,
    }[configuration_format]
    return save_raw_configuration(configuration_path, configuration)


def save_raw_configuration_yaml(configuration_path, configuration):
    yaml = YAML()
    yaml.explicit_start = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    try:
        with configuration_path.open('wt') as configuration_file:
            yaml.dump(configuration, configuration_file)
    except (OSError, YAMLError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration_path


def load_configuration(configuration_path, index=0, group_definitions=[]):
        configuration = AutomationDefinition(
            configuration,
            path=configuration_path,
            index=index,
            group_definitions=group_definitions)


def validate_protocol(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError(
            'crosscompute was not found in the configuration')
    protocol_version = configuration['crosscompute'].strip()
    if not protocol_version:
        raise CrossComputeConfigurationError(
            'crosscompute version is required')
    elif not is_equivalent_version(
            protocol_version, __version__, version_depth=3):
        raise CrossComputeConfigurationError(
            f'crosscompute version {protocol_version} is not compatible with '
            f'{__version__}; pip install crosscompute=={protocol_version}')
    return {}


def validate_automation_identifiers(configuration):
    d = get_dictionary(configuration, 'copyright')
    copyright_name = d.get('name', COPYRIGHT_NAME)
    copyright_uri = d.get('uri', COPYRIGHT_URI)
    copyright_year = d.get('year', COPYRIGHT_YEAR)
    attribution_text = remove_single_paragraph(get_html_from_markdown(
        d.get('text', ATTRIBUTION_TEXT).format(
            name=name,
            copyright_name=copyright_name,
            copyright_uri=copyright_uri,
            copyright_year=copyright_year,
        ), extras=[
            'target-blank-links']))
    return {
        'title': configuration.get('title', name),
        'description': configuration.get('description', name),
        'uri': AUTOMATION_ROUTE.format(automation_slug=slug),
        'copyright_name': copyright_name,
        'copyright_uri': copyright_uri,
        'attribution_text': attribution_text}


def validate_imports(configuration):
    group_definitions = getattr(configuration, 'group_definitions', [])
    automation_configuration = load_configuration(
        path, index=i, group_definitions=group_definitions)


def validate_variables(configuration):
    view_names = set()
    if 'print' in configuration:
        initialize_printer_by_name()
    for step_name in STEP_NAMES:
        if step_name == 'debug':
            variable_dictionaries[:0] = DEBUG_VARIABLE_DICTIONARIES
        variable_definitions = [VariableDefinition(
            _, step_name=step_name) for _ in variable_dictionaries]
        assert_unique_values([
            _.id for _ in variable_definitions
        ], f'variable id "{{x}}" in {step_name}')
        variable_definitions_by_step_name[step_name] = variable_definitions
        view_names.update(_.view_name for _ in variable_definitions)
    L.debug('view_names = %s', list(view_names))
    return {
        '___view_names': view_names}


def validate_variable_views(configuration):
    initialize_view_by_name()
    for view_name in configuration.___view_names:
        try:
            View = view_by_name[view_name]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'view "{view_name}" is not installed')
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
            _.path for _ in template_definitions
        ], f'template path "{{x}}" in {step_name}')
        template_definitions_by_step_name[step_name] = template_definitions
    return {
        'template_definitions_by_step_name': template_definitions_by_step_name}


def validate_environment(configuration):
    package_ids_by_manager_name = get_package_ids_by_manager_name(
        get_dictionaries(d, 'packages'))
    port_definitions = get_port_definitions(
        d, configuration.get_variable_definitions('log')
        + configuration.get_variable_definitions('debug'))
    batch_concurrency_name = d.get('batch', 'thread').lower()
    if batch_concurrency_name not in ('process', 'thread', 'single'):
        raise CrossComputeConfigurationError(
            f'batch concurrency "{batch_concurrency_name}" is not supported')
    interval_timedelta, is_interval_strict = get_interval_pack(d.get(
        'interval', '').strip())
    return {
        'engine_name': get_engine_name(d),
        'parent_image_name': d.get('image', 'python').strip(),
        'package_ids_by_manager_name': package_ids_by_manager_name,
        'port_definitions': port_definitions,
        'environment_variable_ids': environment_variable_ids,
        'batch_concurrency_name': batch_concurrency_name,
        'interval_timedelta': interval_timedelta,
        'is_interval_strict': is_interval_strict}


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
                    f'style path "{path}" was not found')
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
        template_id = raw_template_definition.get(
            'id', template_definition.path.stem)
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
    button_text_by_id = {}
    for button_definition in button_definitions:
        button_id = button_definition.id
        button_text = button_definition.configuration.get(
            'button-text', '').strip()
        if not button_text:
            continue
        button_text_by_id[button_id] = button_text
    return {'button_text_by_id': button_text_by_id}


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


def validate_template_identifiers(template_dictionary):
    try:
        template_path = template_dictionary['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each template')
    automation_folder = template_dictionary.automation_folder
    template_path = Path(template_path)
    if not (automation_folder / template_path).exists():
        raise CrossComputeConfigurationError(
            f'template path "{template_path}" was not found')
    return {
        'path': template_path,
        'expression': template_dictionary.get('expression', '')}


def validate_variable_identifiers(variable_dictionary):
    try:
        variable_path = variable_dictionary['path'].strip()
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each variable')
    if not VARIABLE_ID_PATTERN.match(variable_id):
        raise CrossComputeConfigurationError(
            f'{variable_id} is not a valid variable id; please use only '
            'lowercase, uppercase, numbers, hyphens, underscores and spaces')
    if variable_dictionary.step_name == 'print':
        # TODO: Extract this part
        if view_name in ['link']:
            pass
        elif view_name not in PRINTER_NAMES:
            raise CrossComputeConfigurationError(
                f'printer "{view_name}" is not supported')
        elif view_name not in printer_by_name:
            raise CrossComputeConfigurationError(
                f'pip install crosscompute-printers-{view_name}')
    if not variable_path:
        raise CrossComputeConfigurationError(
            f'variable "{variable_id}" path cannot be empty')
    elif relpath(variable_path).startswith('..'):
        raise CrossComputeConfigurationError(
            f'variable "{variable_id}" path "{variable_path}" must be within '
            'the automation folder')
    label = variable_dictionary.get('label', format_name(variable_id)).strip()
    return {
        'id': variable_id,
        'view_name': view_name,
        'path': Path(variable_path),
        'label': label}


def validate_variable_configuration(variable_dictionary):
    # TODO: Validate variable view configurations
    c = get_dictionary(
        variable_dictionary, 'configuration')
    if 'path' in c:
        p = c['path']
        if not p.endswith('.json'):
            raise CrossComputeConfigurationError(
                f'variable configuration path "{p}" suffix must be ".json"')
    if variable_dictionary.step_name == 'print':
        variable_id = variable_dictionary.id
        view_name = variable_dictionary.view_name
        if view_name == 'link':
            pass
        else:
            process_header_footer_options(variable_id, c)
            process_page_number_options(variable_id, c)
    return {'configuration': c}


def validate_batch_identifiers(batch_dictionary):
    if data_by_id is not None:
        d['uri'] = BATCH_ROUTE.format(batch_slug=slug)


def validate_batch_configuration(batch_dictionary):
    return {
        'clock': Clock()}


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
                    f'dataset reference link "{reference_path}" is invalid')
            elif source_path.name == 'runs':
                source_path.mkdir(parents=True)
            else:
                raise CrossComputeConfigurationError(
                    f'dataset reference path "{reference_path}" was not found')
        target_path = dataset_dictionary.path
        if target_path.exists() and not target_path.is_symlink():
            raise CrossComputeConfigurationError(
                'dataset path conflicts with existing dataset; please delete '
                f'"{target_path}" from the disk to continue')
    return {'reference': dataset_reference}


def validate_script_identifiers(script_dictionary):
    folder = script_dictionary.get('folder', '.').strip()
    if 'path' in script_dictionary:
        path = Path(script_dictionary['path'].strip())
        suffix = path.suffix
        if suffix not in ['.ipynb', '.py']:
            raise CrossComputeConfigurationError(
                f'script path suffix "{suffix}" is not supported')
        method_count += 1
    else:
        path = None
    return {'folder': Path(folder), 'command': command, 'path': path}


def validate_package_identifiers(package_dictionary):
    try:
        package_id = package_dictionary['id']
        manager_name = package_dictionary['manager']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each package')
    if manager_name not in PACKAGE_MANAGER_NAMES:
        raise CrossComputeConfigurationError(
            f'manager "{manager_name}" is not supported')
    return {'id': package_id, 'manager_name': manager_name}


def validate_port_identifiers(port_dictionary):
    try:
        port_id = port_dictionary['id']
        port_number = port_dictionary['number']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each port')
    try:
        port_number = int(port_number)
    except ValueError:
        raise CrossComputeConfigurationError(
            f'port number "{port_number}" must be an integer')
    return {
        'id': port_id,
        'number': port_number}


def validate_style_identifiers(style_dictionary):
    uri = style_dictionary.get('uri', '').strip()
    path = style_dictionary.get('path', '').strip()
    if not uri and not path:
        raise CrossComputeConfigurationError('style uri or path is required')
    return {'uri': uri, 'path': Path(path)}


def validate_page_identifiers(page_dictionary):
    try:
        page_id = page_dictionary['id']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each page')
    if page_id not in DESIGN_NAMES_BY_PAGE_ID:
        raise CrossComputeConfigurationError(
            f'page "{page_id}" is not supported')
    return {'id': page_id}


def validate_page_configuration(page_dictionary):
    page_configuration = get_dictionary(page_dictionary, 'configuration')
    page_id = page_dictionary['id']
    design_name = page_configuration.get('design')
    design_names = DESIGN_NAMES_BY_PAGE_ID[page_id]
    if design_name not in design_names:
        raise CrossComputeConfigurationError(
            f'design "{design_name}" is not supported for page "{page_id}"')
    return {'configuration': page_configuration}


def validate_button_identifiers(button_dictionary):
    try:
        button_id = button_dictionary['id']
    except KeyError as e:
        raise CrossComputeConfigurationError(
            f'{e} is required for each button')
    if button_id not in BUTTON_TEXT_BY_ID:
        raise CrossComputeConfigurationError(
            f'button id "{button_id}" is not supported')
    return {'id': button_id}


def validate_button_configuration(button_dictionary):
    button_configuration = get_dictionary(button_dictionary, 'configuration')
    return {'configuration': button_configuration}


def validate_token_identifiers(token_dictionary):
    try:
        token_path = token_dictionary['path']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} is required for each token')
    path = Path(token_dictionary.automation_folder, token_path)
    suffix = path.suffix
    if suffix == '.yml':
        d = load_raw_configuration_yaml(path)
    else:
        raise CrossComputeConfigurationError(
            f'token path suffix "{suffix}" is not supported')
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
                    f'environment variable "{variable_id}" is missing')
                e.path = path
                raise e
        identities_by_token[token] = identities
    return {'identities_by_token': identities_by_token}


def validate_group_identifiers(group_dictionary):
    try:
        group_configuration = group_dictionary['configuration']
    except KeyError as e:
        raise CrossComputeConfigurationError(f'{e} is required for each group')
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
            f'{e} is required for each permission')
    if permission_id not in PERMISSION_IDS:
        raise CrossComputeConfigurationError(
            f'permission id "{permission_id}" is not supported')
    permission_action = permission_dictionary.get('action', 'accept')
    if permission_action not in PERMISSION_ACTIONS:
        raise CrossComputeConfigurationError(
            f'permission action "{permission_action}" is not supported')
    return {'id': permission_id, 'action': permission_action}


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
            f'engine "{engine_name}" is not supported')
    return engine_name


def get_package_ids_by_manager_name(package_dictionaries):
    package_ids_by_manager_name = defaultdict(set)
    package_definitions = [PackageDefinition(_) for _ in package_dictionaries]
    for package_definition in package_definitions:
        manager_name = package_definition.manager_name
        package_ids_by_manager_name[manager_name].add(package_definition.id)
    return package_ids_by_manager_name


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
                f'port "{port_id}" must correspond to a log or debug variable')
        port_definition.step_name = variable_definition.step_name
    return port_definitions


def get_interval_pack(interval_text):
    if not interval_text:
        return None, None
    try:
        count, name = interval_text.split(maxsplit=1)
        count = int(count)
    except ValueError:
        raise CrossComputeConfigurationError(
            f'interval "{interval_text}" is not parsable; '
            f'something like "30 minutes" was expected')
    for unit_name in INTERVAL_UNIT_NAMES:
        if name.startswith(unit_name[:-1]):
            break
    else:
        unit_names_text = ' or '.join(INTERVAL_UNIT_NAMES)
        raise CrossComputeConfigurationError(
            f'interval "{interval_text}" unit "{name}" is not supported; '
            f'{unit_names_text} was expected')
    is_strict = True if '!' in name else False
    return timedelta(**{unit_name: count}), is_strict


def process_header_footer_options(variable_id, print_configuration):
    k = 'header-footer'
    d = get_dictionary(print_configuration, k)
    d['skip-first'] = bool(d.get('skip-first'))


def process_page_number_options(variable_id, print_configuration):
    k = 'page-number'
    d = get_dictionary(print_configuration, k)
    location = d.get('location')
    if location and location not in ['header', 'footer']:
        raise CrossComputeConfigurationError(
            f'print variable "{variable_id}" configuration "{k}" '
            f'location "{location}" is not supported')
    alignment = d.get('alignment')
    if alignment and alignment not in ['left', 'center', 'right']:
        raise CrossComputeConfigurationError(
            f'print variable "{variable_id}" configuration "{k}" '
            f'alignment "{alignment}" is not supported')


def get_folder_plus_path(d):
    folder = d.get('folder', '').strip()
    path = d.get('path', '').strip()
    if not folder and not path:
        return
    return Path(folder, path)


f'"{key}" must be dictionaries'
f'"{key}" must be a dictionary'
f'"{key}" must be a list'


PERMISSION_IDS = [
    'add_token',
    'see_root',
    'see_automation',
    'see_batch',
    'run_automation']
PERMISSION_ACTIONS = [
    'accept',
    'match']

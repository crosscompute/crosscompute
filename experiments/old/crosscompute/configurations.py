import codecs
import re
import sys
from collections import OrderedDict
from fnmatch import fnmatch
from invisibleroads_macros.configuration import (
    RawCaseSensitiveConfigParser, format_settings, load_relative_settings,
    load_settings, make_absolute_paths, make_relative_paths, save_settings)
from invisibleroads_macros.descriptor import cached_property
from invisibleroads_macros.disk import (
    are_same_path, get_absolute_path, link_safely)
from invisibleroads_macros.exceptions import BadPath
from invisibleroads_macros.log import (
    filter_nested_dictionary, format_path, get_log,
    parse_nested_dictionary_from, parse_raw_dictionary)
from invisibleroads_macros.shell import make_executable
from invisibleroads_macros.table import normalize_key
from invisibleroads_macros.text import (
    has_whitespace, split_shell_command, unicode_safely)
from os import getcwd, walk
from os.path import basename, dirname, isabs, join
from pyramid.settings import asbool, aslist
from six import text_type

from .exceptions import (
    DataParseError, DataTypeError, ToolConfigurationNotFound,
    ToolConfigurationNotValid, ToolNotFound, ToolNotSpecified)
from .symmetries import (
    prepare_path_argument, suppress, COMMAND_LINE_JOIN, SCRIPT_EXTENSION)
from .types import get_data_type, RESERVED_ARGUMENT_NAMES


TOOL_NAME_PATTERN = re.compile(r'crosscompute\s*(.*)')
ARGUMENT_PATTERN = re.compile(r'(\{\s*.+?\s*\})')
L = get_log(__name__)


class ResultConfiguration(object):

    def __init__(self, result_folder, quiet=False):
        self.result_folder = result_folder
        self.quiet = quiet

    def save_tool_location(self, tool_definition, tool_id=None):
        configuration_folder = tool_definition['configuration_folder']
        with suppress(ValueError):
            link_safely(join(self.result_folder, 'f'), configuration_folder)
        tool_location = {
            'configuration_folder': configuration_folder,
            'tool_name': tool_definition['tool_name'],
        }
        if tool_id:
            tool_location['tool_id'] = tool_id
        d = {'tool_location': tool_location}
        if not self.quiet:
            print(format_settings(d))
            print('')
        tool_location['configuration_folder'] = 'f'
        return save_settings(join(self.result_folder, 'f.cfg'), d)

    def save_result_arguments(
            self, tool_definition, result_arguments, environment=None,
            external_folders=None):
        d = {'result_arguments': OrderedDict((
            k, get_data_type(k).render(v)
        ) for k, v in result_arguments.items())}
        if environment:
            d['environment_variables'] = environment
        if not self.quiet:
            print(format_settings(d))
            print('')
        d = filter_nested_dictionary(d, lambda x: x.startswith(
            '_') or x in RESERVED_ARGUMENT_NAMES)
        d = make_relative_paths(d, self.result_folder, external_folders or [
            tool_definition['configuration_folder'],
        ])
        return save_settings(join(self.result_folder, 'x.cfg'), d)

    def save_result_properties(self, result_properties):
        d = {'result_properties': result_properties}
        if not self.quiet:
            print(format_settings(d))
        d = filter_nested_dictionary(d, lambda x: x.startswith('_'))
        d = make_relative_paths(d, self.result_folder)
        return save_settings(join(self.result_folder, 'y.cfg'), d)

    def save_result_scripts(self, tool_definition, result_arguments):
        command_template = tool_definition['command_template']
        if not self.quiet:
            print('[result_scripts]')
        self.save_script(
            'x', 'command', command_template, tool_definition,
            result_arguments)
        if command_template.startswith('python'):
            debugger_command = 'pudb' if sys.version_info[0] < 3 else 'pudb3'
            debugger_template = re.sub(
                r'^python', debugger_command, command_template)
            self.save_script(
                'x-debugger', 'debugger', debugger_template, tool_definition,
                result_arguments)
        if not self.quiet:
            print('')

    def save_script(
            self, script_name, command_name, command_template, tool_definition,
            result_arguments):
        target_path = join(self.result_folder, script_name + SCRIPT_EXTENSION)
        command_parts = [
            'cd "%s"' % tool_definition['configuration_folder'],
            render_command(command_template.replace(
                '\n', ' %s\n' % COMMAND_LINE_JOIN), result_arguments)]
        with codecs.open(target_path, 'w', encoding='utf-8') as target_file:
            target_file.write('\n'.join(command_parts) + '\n')
        if not self.quiet:
            print(command_name + '_path = %s' % format_path(target_path))
        return make_executable(target_path)

    @cached_property
    def tool_definition(self):
        return load_tool_definition(join(self.result_folder, 'f.cfg'))

    @cached_property
    def result_arguments(self):
        return load_result_arguments(join(
            self.result_folder, 'x.cfg'), self.tool_definition)

    @cached_property
    def result_properties(self):
        return load_result_properties(join(self.result_folder, 'y.cfg'))


def find_tool_definition_by_name(folder, default_tool_name=None):
    tool_definition_by_name = {}
    folder = unicode_safely(folder)
    default_tool_name = unicode_safely(default_tool_name)
    for root_folder, folder_names, file_names in walk(folder):
        if are_same_path(root_folder, folder):
            tool_name = default_tool_name or basename(folder)
        else:
            tool_name = basename(root_folder)
        for file_name in file_names:
            if not fnmatch(file_name, '*.ini'):
                continue
            try:
                tool_configuration_path = get_absolute_path(
                    file_name, root_folder)
            except BadPath:
                L.warning('link skipped (%s)' % join(root_folder, file_name))
                continue
            for tool_name, tool_definition in load_tool_definition_by_name(
                    tool_configuration_path, tool_name).items():
                tool_name = _get_unique_tool_name(
                    tool_name, tool_definition_by_name)
                tool_definition_by_name[tool_name] = tool_definition
    return tool_definition_by_name


def find_tool_definition(folder=None, tool_name='', default_tool_name=''):
    tool_definition_by_name = find_tool_definition_by_name(
        folder or getcwd(), default_tool_name)
    if not tool_definition_by_name:
        raise ToolConfigurationNotFound(
            'Tool configuration not found. Run this command in a folder '
            'with a tool configuration file or in a parent folder.')
    if len(tool_definition_by_name) == 1:
        return list(tool_definition_by_name.values())[0]
    if not tool_name:
        raise ToolNotSpecified('Tool not specified. {}'.format(
            format_available_tools(tool_definition_by_name)))
    tool_name = tool_name or tool_definition_by_name.keys()[0]
    try:
        tool_definition = tool_definition_by_name[tool_name]
    except KeyError:
        raise ToolNotFound('Tool not found ({}). {}'.format(
            tool_name, format_available_tools(tool_definition_by_name)))
    return tool_definition


def load_tool_definition_by_name(
        tool_configuration_path, default_tool_name=None):
    tool_definition_by_name = {}
    configuration = RawCaseSensitiveConfigParser()
    configuration.read(tool_configuration_path, 'utf-8')
    configuration_folder = dirname(tool_configuration_path)
    for section_name in configuration.sections():
        try:
            tool_name = _parse_tool_name(section_name, default_tool_name)
        except ToolConfigurationNotValid as e:
            continue
        try:
            tool_definition = _parse_tool_definition(dict(configuration.items(
                section_name)), configuration_folder, tool_name)
        except ToolConfigurationNotValid as e:
            L.warning('tool skipped (configuration_path=%s, tool_name=%s) ' % (
                tool_configuration_path, tool_name) + str(e))
            continue
        tool_definition_by_name[tool_name] = tool_definition
    return tool_definition_by_name


def load_tool_definition(result_configuration_path):
    s = load_settings(result_configuration_path, 'tool_location')
    try:
        tool_configuration_folder = s['configuration_folder']
        tool_name = s['tool_name']
    except KeyError:
        raise ToolConfigurationNotFound
    if not isabs(tool_configuration_folder):
        result_configuration_folder = dirname(result_configuration_path)
        tool_configuration_folder = join(
            result_configuration_folder, tool_configuration_folder)
    return find_tool_definition(tool_configuration_folder, tool_name)


def load_result_arguments(result_configuration_path, tool_definition):
    results_folder = dirname(dirname(result_configuration_path))
    external_folders = [
        tool_definition['configuration_folder'],
        results_folder]
    arguments = load_relative_settings(
        result_configuration_path, 'result_arguments', external_folders)
    arguments.pop('target_folder', None)
    result_configuration_folder = dirname(result_configuration_path)
    try:
        d = parse_data_dictionary_from(
            arguments, result_configuration_folder, external_folders,
            tool_definition)
    except DataParseError as e:
        d = e.value_by_key
        for k, v in e.message_by_name.items():
            L.warning(
                'argument skipped (' +
                'configuration_path=%s ' % result_configuration_path +
                'argument_name=%s ' % k +
                'error_message=%s)' % v)
            del d[k]
    return d


def load_result_properties(result_configuration_path):
    properties = load_relative_settings(
        result_configuration_path, 'result_properties')
    return parse_nested_dictionary_from(properties, max_depth=1)


def format_available_tools(tool_definition_by_name):
    tool_count = len(tool_definition_by_name)
    return '{} available:\n{}'.format(
        tool_count, '\n'.join(tool_definition_by_name))


def parse_data_dictionary(
        text, root_folder, external_folders=None, tool_definition=None):
    d = parse_raw_dictionary(
        text, is_key=lambda x: ':' not in x and ' ' not in x)
    return parse_data_dictionary_from(
        d, root_folder, external_folders, tool_definition)


def parse_data_dictionary_from(
        raw_dictionary, root_folder, external_folders=None,
        tool_definition=None):
    if tool_definition:
        def get_default_value_for(key):
            return get_default_value(key, tool_definition)
    else:
        def get_default_value_for(key):
            return
    d = make_absolute_paths(raw_dictionary, root_folder, external_folders)
    errors = OrderedDict()
    for key, value in d.items():
        if key in RESERVED_ARGUMENT_NAMES:
            continue
        data_type = get_data_type(key)
        try:
            default_value = get_default_value_for(key)
            value = data_type.parse_safely(value, default_value)
        except DataTypeError as e:
            errors[key] = text_type(e)
        d[key] = value
    if errors:
        raise DataParseError(errors, d)
    return d


def get_default_key(key, tool_definition):
    for prefix in 'x.', '':
        default_key = prefix + key
        if default_key in tool_definition:
            return default_key
        default_key = prefix + key + '_path'
        if default_key in tool_definition:
            return default_key


def get_default_value(key, tool_definition):
    data_type = get_data_type(key)
    for prefix in 'x.', '':
        default_key = prefix + key
        if default_key in tool_definition:
            return data_type.parse_safely(tool_definition[default_key])
        default_key = prefix + key + '_path'
        if default_key in tool_definition:
            return data_type.load(tool_definition[default_key])


def render_command(command_template, result_arguments):
    d = {}
    quote_pattern = re.compile(r"""["'].*["']""")
    for k, v in result_arguments.items():
        v = get_data_type(k).render(v)
        if k.endswith('_path') or k.endswith('_folder'):
            v = prepare_path_argument(v)
        if not v or (has_whitespace(v) and not quote_pattern.match(v)):
            v = '"%s"' % v
        d[k] = v
    return command_template.format(**d)


def _get_unique_tool_name(tool_name, existing_tool_names):
    suggested_tool_name = tool_name
    i = 2
    while True:
        if suggested_tool_name not in existing_tool_names:
            break
        suggested_tool_name = '%s-%s' % (tool_name, i)
        i += 1
    return suggested_tool_name


def _parse_tool_name(configuration_section_name, default_tool_name=None):
    match = TOOL_NAME_PATTERN.match(configuration_section_name)
    if not match:
        raise ToolConfigurationNotValid
    tool_name = match.group(1).strip() or default_tool_name or ''
    return normalize_key(tool_name, word_separator='-')


def _parse_tool_definition(value_by_key, configuration_folder, tool_name):
    try:
        command_template = value_by_key['command_template'].strip()
    except KeyError as e:
        raise ToolConfigurationNotValid('command_template required')
    if not command_template:
        raise ToolConfigurationNotValid('command_template expected')
    d = _parse_tool_arguments(value_by_key)
    d['configuration_folder'] = configuration_folder
    d['tool_name'] = tool_name
    d['show_raw_output'] = asbool(value_by_key.get('show_raw_output'))
    d['ignored_outputs'] = aslist(value_by_key.get('ignored_outputs', []))
    for k, v in make_absolute_paths(d, configuration_folder).items():
        if k in ('argument_names', 'show_raw_output', 'ignored_outputs'):
            continue
        v = v.strip()
        if k.endswith('_path') and not v:
            raise ToolConfigurationNotValid('file not found (%s=%s)' % (k, v))
        d[unicode_safely(k)] = unicode_safely(v)
    return d


def _parse_tool_arguments(value_by_key):
    d = value_by_key.copy()
    terms, argument_names = [], []
    for term in ARGUMENT_PATTERN.split(value_by_key['command_template']):
        term = term.strip()
        if not term:
            continue
        if not term.startswith('{') and not term.endswith('}'):
            terms.extend(_split_term(term))
            continue
        argument_string = term.strip('{ }')
        if not argument_string:
            continue
        argument_parts = argument_string.split(' ', 1)
        argument_head = argument_parts[0]
        argument_name = argument_head.lstrip('-')
        argument_key = get_default_key(argument_name, value_by_key)
        if not argument_key and len(argument_parts) > 1:
            argument_value = argument_parts[1]
            d['x.%s' % argument_name] = argument_value
        if argument_head.startswith('--'):
            term = '--%s {%s}' % (argument_name, argument_name)
        else:
            term = '{%s}' % argument_name
        _append_term(term, terms)
        argument_names.append(argument_name)
    d['command_template'] = '\n'.join(terms).strip()
    d['argument_names'] = argument_names
    return d


def _split_term(term):
    ys = []
    for x in split_shell_command(term):
        if x.startswith('--') or ' ' not in x:
            y = x
        else:
            y = '"%s"' % x
        ys.append(y)
    return ys


def _append_term(term, terms):
    conditions = (
        terms and not term.startswith('--') and
        terms[-1].startswith('--') and not terms[-1].endswith('}'))
    if conditions:
        terms[-1] += ' ' + term
    else:
        terms.append(term)

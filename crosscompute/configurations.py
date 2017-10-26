import codecs
import re
from collections import OrderedDict
from fnmatch import fnmatch
from invisibleroads_macros.configuration import (
    RawCaseSensitiveConfigParser, format_settings, load_relative_settings,
    make_absolute_paths, make_relative_paths, save_settings)
from invisibleroads_macros.descriptor import cached_property
from invisibleroads_macros.disk import are_same_path, link_path
from invisibleroads_macros.log import (
    filter_nested_dictionary, format_path, get_log, parse_nested_dictionary,
    parse_nested_dictionary_from)
from invisibleroads_macros.text import has_whitespace, unicode_safely
from os import getcwd, walk
from os.path import basename, dirname, isabs, join
from pyramid.settings import asbool
from six import text_type

from .exceptions import (
    DataParseError, DataTypeError, ToolConfigurationNotFound, ToolNotFound,
    ToolNotSpecified)
from .symmetries import (
    prepare_path_argument, suppress, COMMAND_LINE_JOIN, SCRIPT_EXTENSION)
from .types import get_data_type, RESERVED_ARGUMENT_NAMES


TOOL_NAME_PATTERN = re.compile(r'crosscompute\s*(.*)')
ARGUMENT_NAME_PATTERN = re.compile(r'\{(.+?)\}')
L = get_log(__name__)


class ResultConfiguration(object):

    def __init__(self, result_folder, quiet=False):
        self.result_folder = result_folder
        self.quiet = quiet

    def save_tool_location(self, tool_definition, tool_id=None):
        with suppress(ValueError):
            link_path(join(self.result_folder, 'f'), tool_definition[
                'configuration_folder'])
        configuration_path = tool_definition['configuration_path']
        tool_location = {
            'configuration_path': configuration_path,
            'tool_name': tool_definition['tool_name'],
        }
        if tool_id:
            tool_location['tool_id'] = tool_id
        d = {'tool_location': tool_location}
        if not self.quiet:
            print(format_settings(d))
            print('')
        tool_location['configuration_path'] = join('f', basename(
            configuration_path))
        return save_settings(join(self.result_folder, 'f.cfg'), d)

    def save_result_arguments(self, result_arguments, environment):
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
        d = make_relative_paths(d, self.result_folder)
        return save_settings(join(self.result_folder, 'x.cfg'), d)

    def save_result_properties(self, result_properties):
        d = {'result_properties': result_properties}
        if not self.quiet:
            print(format_settings(d))
        d = filter_nested_dictionary(d, lambda x: x.startswith('_'))
        d = make_relative_paths(d, self.result_folder)
        return save_settings(join(self.result_folder, 'y.cfg'), d)

    def save_result_script(self, tool_definition, result_arguments):
        target_path = join(self.result_folder, 'x' + SCRIPT_EXTENSION)
        command_parts = [
            'cd "%s"' % tool_definition['configuration_folder'],
            render_command(tool_definition['command_template'].replace(
                '\n', ' %s\n' % COMMAND_LINE_JOIN), result_arguments)]
        with codecs.open(target_path, 'w', encoding='utf-8') as target_file:
            target_file.write('\n'.join(command_parts) + '\n')
        if not self.quiet:
            print('command_path = %s' % format_path(target_path))
        return target_path

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
            tool_configuration_path = join(root_folder, file_name)
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
    d = {
        u'configuration_path': tool_configuration_path,
        u'configuration_folder': configuration_folder,
    }
    for section_name in configuration.sections():
        try:
            tool_name = TOOL_NAME_PATTERN.match(section_name).group(1).strip()
        except AttributeError:
            continue
        if not tool_name:
            tool_name = default_tool_name
        tool_definition = {
            unicode_safely(k): unicode_safely(v)
            for k, v in configuration.items(section_name)}
        tool_definition[u'show_raw_output'] = asbool(tool_definition.get(
            'show_raw_output'))
        tool_definition[u'tool_name'] = tool_name
        tool_definition[u'argument_names'] = parse_tool_argument_names(
            tool_definition.get('command_template', u''))
        tool_definition_by_name[tool_name] = dict(make_absolute_paths(
            tool_definition, configuration_folder), **d)
    return tool_definition_by_name


def load_tool_definition(result_configuration_path):
    s = load_relative_settings(result_configuration_path, 'tool_location')
    tool_configuration_path = s['configuration_path']
    tool_name = s['tool_name']
    if not isabs(tool_configuration_path):
        result_configuration_folder = dirname(result_configuration_path)
        tool_configuration_path = join(
            result_configuration_folder, tool_configuration_path)
    tool_definition_by_name = load_tool_definition_by_name(
        tool_configuration_path, tool_name)
    return tool_definition_by_name[tool_name]


def load_result_arguments(result_configuration_path, tool_definition):
    arguments = load_relative_settings(
        result_configuration_path, 'result_arguments')
    arguments.pop('target_folder', None)
    result_configuration_folder = dirname(result_configuration_path)
    return parse_data_dictionary_from(
        arguments, result_configuration_folder, tool_definition)


def load_result_properties(result_configuration_path):
    properties = load_relative_settings(
        result_configuration_path, 'result_properties')
    return parse_nested_dictionary_from(properties, max_depth=1)


def format_available_tools(tool_definition_by_name):
    tool_count = len(tool_definition_by_name)
    return '{} available:\n{}'.format(
        tool_count, '\n'.join(tool_definition_by_name))


def parse_tool_argument_names(command_template):
    return tuple(ARGUMENT_NAME_PATTERN.findall(command_template))


def parse_data_dictionary(text, root_folder, tool_definition=None):
    d = parse_nested_dictionary(
        text, is_key=lambda x: ':' not in x and ' ' not in x)
    return parse_data_dictionary_from(d, root_folder, tool_definition)


def parse_data_dictionary_from(
        raw_dictionary, root_folder, tool_definition=None):
    if tool_definition:
        def get_default_value_for(key):
            return get_default_value(key, tool_definition)
    else:
        def get_default_value_for(key):
            return
    d = make_absolute_paths(raw_dictionary, root_folder)
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


def has_default_value(key, tool_definition):
    for prefix in 'x.', '':
        default_key = prefix + key
        if default_key in tool_definition:
            return True
        default_key = prefix + key + '_path'
        if default_key in tool_definition:
            return True
    return False


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

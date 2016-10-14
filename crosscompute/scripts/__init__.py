import codecs
import logging
import os
import re
import simplejson as json
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
import sys
import time
from collections import OrderedDict
from invisibleroads.scripts import (
    Script, StoicArgumentParser, configure_subparsers, get_scripts_by_name,
    run_scripts)
from invisibleroads_macros.configuration import (
    RawCaseSensitiveConfigParser, split_arguments, unicode_safely)
from invisibleroads_macros.disk import cd, make_enumerated_folder, make_folder
from invisibleroads_macros.iterable import merge_dictionaries
from invisibleroads_macros.log import (
    format_hanging_indent, format_summary, parse_nested_dictionary_from,
    sort_dictionary)
from os.path import abspath, basename, isabs, join, splitext
from six import text_type
from tempfile import gettempdir

from ..configurations import (
    find_tool_definition, load_result_arguments, load_tool_definition)
from ..exceptions import CrossComputeError, DataParseError
from ..fallbacks import (
    COMMAND_LINE_JOIN, SCRIPT_EXTENSION, SCRIPT_ENVIRONMENT,
    prepare_path_argument)
from ..types import initialize_data_types, parse_data_dictionary
from .convert import prepare_tool_from_notebook


EXCLUDED_FILE_NAMES = [
    'run.bat',
    'run.sh',
    'standard_output.log',
    'standard_error.log',
]


class ToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument(
            'tool_name', nargs='?', type=unicode_safely, default='')
        argument_subparser.add_argument(
            '--data_folder', metavar='FOLDER', type=unicode_safely)
        argument_subparser.add_argument(
            '--suffix_by_data_type', metavar='JSON', type=json.loads)
        argument_subparser.add_argument(
            '--verbose', action='store_true')

    def run(self, args):
        initialize_data_types(args.suffix_by_data_type)
        tool_definition = prepare_tool_definition(args.tool_name)
        tool_name = tool_definition['tool_name']
        data_folder = args.data_folder or join(
            gettempdir(), 'crosscompute', tool_name)
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.WARNING)
        return tool_definition, data_folder


class _ResultConfiguration(object):

    def __init__(self, target_folder):
        self.target_folder = make_folder(target_folder)
        self.target_file = codecs.open(
            join(target_folder, 'result.cfg'), 'w', encoding='utf-8')

    def write(self, screen_text, file_text=None):
        _write(self.target_file, screen_text, file_text)

    def write_header(self, tool_definition, result_arguments):
        configuration_folder = tool_definition['configuration_folder']
        tool_argument_names = list(tool_definition['argument_names'])
        # Write tool_definition
        template = '[tool_definition]\n%s'
        command_path = self.write_script(tool_definition, result_arguments)
        self.write(template % format_summary(OrderedDict([
            ('tool_name', tool_definition['tool_name']),
            ('configuration_path', tool_definition['configuration_path']),
        ])))
        print(format_summary({'command_path': command_path}))
        # Put target_folder at end of result_arguments
        target_folder = result_arguments['target_folder']
        try:
            tool_argument_names.remove('target_folder')
        except ValueError:
            pass
        result_arguments = sort_dictionary(
            result_arguments, tool_argument_names)
        # Write result_arguments
        template = '\n[result_arguments]\n%s\n'
        result_arguments['target_folder'] = target_folder
        for k, v in result_arguments.items():
            if not k.endswith('_path') or isabs(v):
                continue
            result_arguments[k] = abspath(join(configuration_folder, v))
        self.write(template % format_summary(result_arguments))

    def write_script(self, tool_definition, result_arguments):
        configuration_folder = tool_definition['configuration_folder']
        script_path = join(self.target_folder, 'run' + SCRIPT_EXTENSION)
        command = render_command(
            tool_definition['command_template'], result_arguments)
        with codecs.open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write('cd "%s"\n' % configuration_folder)
            script_file.write(format_hanging_indent(
                command.replace('\n', ' %s\n' % COMMAND_LINE_JOIN)) + '\n')
        return script_path

    def write_footer(self, result_properties):
        template = '[result_properties]\n%s'
        self.write(
            screen_text=template % format_summary(
                result_properties, censored=False),
            file_text=template % format_summary(
                result_properties, censored=True))


def launch(argv=sys.argv):
    argument_parser = StoicArgumentParser('crosscompute', add_help=False)
    argument_subparsers = argument_parser.add_subparsers(dest='command')
    scripts_by_name = get_scripts_by_name('crosscompute')
    configure_subparsers(argument_subparsers, scripts_by_name)
    args = argument_parser.parse_known_args(argv[1:])[0]
    run_scripts(scripts_by_name, args)


def prepare_tool_definition(tool_name):
    if tool_name.endswith('.cfg'):
        tool_definition = load_tool_definition(tool_name)
        result_arguments = load_result_arguments(tool_name)
        return merge_dictionaries(tool_definition, result_arguments)
    elif tool_name.endswith('.ipynb'):
        tool_name = prepare_tool_from_notebook(tool_name)
    if tool_name:
        tool_name = tool_name.rstrip(os.sep)  # Remove folder slash
        tool_name = tool_name.replace('_', '-')
        tool_name = splitext(tool_name)[0]
    try:
        tool_definition = find_tool_definition(tool_name=tool_name)
    except CrossComputeError as e:
        sys.exit(e)
    return tool_definition


def load_result_configuration(result_folder):
    result_configuration = RawCaseSensitiveConfigParser()
    result_configuration.read(join(result_folder, 'result.cfg'))
    result_arguments = OrderedDict(
        result_configuration.items('result_arguments'))
    result_properties = parse_nested_dictionary_from(OrderedDict(
        result_configuration.items('result_properties')), max_depth=1)
    return result_arguments, result_properties


def prepare_target_folder(data_folder):
    result_id = prepare_result_id(data_folder)
    return get_target_folder(data_folder, result_id)


def prepare_result_id(data_folder):
    parent_folder = join(data_folder, 'results')
    result_folder = make_enumerated_folder(parent_folder)
    result_id = basename(result_folder)
    return result_id


def get_source_folder(data_folder, result_id):
    return join(data_folder, 'results', result_id, 'x')


def get_target_folder(data_folder, result_id):
    return join(data_folder, 'results', result_id, 'y')


def run_script(
        target_folder, tool_definition, result_arguments, environment=None):
    result_properties, timestamp = OrderedDict(), time.time()
    result_arguments = dict(result_arguments, target_folder=target_folder)
    result_configuration = _ResultConfiguration(target_folder)
    result_configuration.write_header(tool_definition, result_arguments)
    command_terms = split_arguments(render_command(tool_definition[
        'command_template'], result_arguments).replace('\n', ' '))
    try:
        with cd(tool_definition['configuration_folder']):
            command_process = subprocess.Popen(
                command_terms, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=environment or SCRIPT_ENVIRONMENT)
    except OSError:
        standard_output, standard_error = None, 'Command not found'
    else:
        standard_output, standard_error = [
            x.rstrip().decode('utf-8') for x in command_process.communicate()]
        if command_process.returncode:
            result_properties['return_code'] = command_process.returncode
    result_properties.update(_process_streams(
        standard_output, standard_error, target_folder, tool_definition))
    result_properties['execution_time_in_seconds'] = time.time() - timestamp
    result_configuration.write_footer(result_properties)
    return result_properties


def render_command(command_template, result_arguments):
    d = {}
    quote_pattern = re.compile(r"""["'].*["']""")
    for k, v in result_arguments.items():
        v = text_type(v).strip()
        if k.endswith('_path') or k.endswith('_folder'):
            v = prepare_path_argument(v)
        if ' ' in v and not quote_pattern.match(v):
            v = '"%s"' % v
        d[k] = v
    return command_template.format(**d)


def _process_streams(
        standard_output, standard_error, target_folder, tool_definition):
    d, type_errors = OrderedDict(), OrderedDict()
    for stream_name, stream_content in [
            ('standard_output', standard_output),
            ('standard_error', standard_error)]:
        if not stream_content:
            continue
        _write(
            codecs.open(join(
                target_folder, '%s.log' % stream_name), 'w', encoding='utf-8'),
            screen_text='[%s]\n%s\n' % (stream_name, stream_content),
            file_text=stream_content)
        try:
            value_by_key = parse_data_dictionary(stream_content, target_folder)
        except DataParseError as e:
            for k, v in e.message_by_name.items():
                type_errors['%s.error' % k] = v
            value_by_key = e.value_by_key
        if tool_definition.get('show_' + stream_name):
            d[stream_name] = stream_content
        if value_by_key:
            d[stream_name + 's'] = value_by_key
    if type_errors:
        d['type_errors'] = type_errors
    return d


def _write(target_file, screen_text, file_text=None):
    if not file_text:
        file_text = screen_text
    print(screen_text)
    target_file.write(file_text + '\n')

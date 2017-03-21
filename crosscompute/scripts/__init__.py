import logging
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
    split_arguments, SECTION_TEMPLATE)
from invisibleroads_macros.disk import (
    cd, copy_text, link_path, make_folder, COMMAND_LINE_HOME, HOME_FOLDER)
from invisibleroads_macros.iterable import merge_dictionaries
from invisibleroads_macros.text import unicode_safely
from os.path import abspath, basename, exists, isabs, join
from stevedore.extension import ExtensionManager

from ..configurations import (
    ResultConfiguration, load_result_arguments, load_tool_definition,
    parse_data_dictionary, render_command)
from ..exceptions import CrossComputeError, DataParseError
from ..extensions import DefaultTool
from ..symmetries import SCRIPT_ENVIRONMENT
from ..types import initialize_data_types


class ToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument(
            'tool_name', nargs='?', type=unicode_safely, default='')
        argument_subparser.add_argument(
            '--data_folder', metavar='FOLDER', type=unicode_safely)
        argument_subparser.add_argument(
            '--suffix_by_data_type', metavar='JSON', type=json.loads)
        argument_subparser.add_argument('--debug', action='store_true')

    def run(self, args):
        initialize_data_types(args.suffix_by_data_type)
        tool_definition = prepare_tool_definition(args.tool_name, args.debug)
        tool_name = tool_definition['tool_name']
        data_folder = args.data_folder or join(
            HOME_FOLDER, '.crosscompute', tool_name)
        logging.basicConfig(level=logging.WARNING)
        return tool_definition, data_folder


def launch(argv=sys.argv):
    argument_parser = StoicArgumentParser('crosscompute', add_help=False)
    argument_subparsers = argument_parser.add_subparsers(dest='command')
    scripts_by_name = get_scripts_by_name('crosscompute')
    configure_subparsers(argument_subparsers, scripts_by_name)
    args = argument_parser.parse_known_args(argv[1:])[0]
    run_scripts(scripts_by_name, args)


def prepare_tool_definition(tool_name, debug=False):
    if exists('f.cfg'):
        tool_definition = load_tool_definition('f.cfg')
        tool_definition.update(load_result_arguments('x.cfg', tool_definition))
        return tool_definition

    for x in ExtensionManager('crosscompute.extensions').extensions:
        if tool_name.endswith('.' + x.name):
            ToolExtension = x.plugin
            break
    else:
        ToolExtension = DefaultTool

    try:
        tool_definition = ToolExtension.prepare_tool_definition(
            tool_name, debug)
    except CrossComputeError as e:
        exit(e)
    return tool_definition


def corral_arguments(argument_folder, result_arguments, use=link_path):
    d = result_arguments.copy()
    make_folder(argument_folder)
    for k, v in result_arguments.items():
        if k.endswith('_path'):
            assert isabs(v)
            d[k] = use(join(argument_folder, basename(v)), v)
    return d


def run_script(
        tool_definition, result_arguments, result_folder, target_folder=None,
        environment=None, quietly=False):
    timestamp, environment = time.time(), environment or {}
    if 'target_folder' in tool_definition['argument_names']:
        y = make_folder(abspath(target_folder or join(result_folder, 'y')))
        result_arguments = OrderedDict(result_arguments, target_folder=y)
    # Record
    result_configuration = ResultConfiguration(result_folder, quietly)
    result_configuration.save_tool_location(tool_definition)
    result_configuration.save_result_arguments(result_arguments, environment)
    # Run
    command_terms = split_arguments(render_command(tool_definition[
        'command_template'].replace('\n', ' '), result_arguments))
    result_properties = OrderedDict()
    try:
        with cd(tool_definition['configuration_folder']):
            command_process = subprocess.Popen(
                command_terms, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=merge_dictionaries(environment, SCRIPT_ENVIRONMENT))
    except OSError:
        stdout, stderr = None, 'Command not found'
    else:
        stdout, stderr = [x.rstrip().decode(
            'utf-8') for x in command_process.communicate()]
        if command_process.returncode:
            result_properties['return_code'] = command_process.returncode
    # Save
    result_properties.update(_process_streams(
        stdout, stderr, result_folder, tool_definition, quietly))
    result_properties['execution_time_in_seconds'] = time.time() - timestamp
    result_configuration.save_result_properties(result_properties)
    result_configuration.save_result_script(tool_definition, result_arguments)
    if 'target_folder' in tool_definition['argument_names']:
        link_path(join(result_folder, 'y'), result_arguments['target_folder'])
    return result_properties


def _process_streams(
        stdout, stderr, result_folder, tool_definition, quietly=False):
    d, type_errors = OrderedDict(), OrderedDict()
    for file_name, stream_name, stream_content in [
            ('stdout.log', 'standard_output', stdout),
            ('stderr.log', 'standard_error', stderr)]:
        if not stream_content:
            continue
        stream_content = stream_content.replace(HOME_FOLDER, COMMAND_LINE_HOME)
        copy_text(join(result_folder, file_name), stream_content + '\n')
        if not quietly:
            print(SECTION_TEMPLATE % (stream_name, stream_content))
        try:
            value_by_key = parse_data_dictionary(
                stream_content, join(result_folder, 'y'), tool_definition)
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

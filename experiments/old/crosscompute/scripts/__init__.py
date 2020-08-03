import logging
import simplejson as json
import sys
import time
from collections import OrderedDict
from fnmatch import fnmatch
from invisibleroads.scripts import (
    Script, StoicArgumentParser, configure_subparsers, get_scripts_by_name,
    run_scripts)
from invisibleroads_macros.configuration import (
    split_arguments, SECTION_TEMPLATE)
from invisibleroads_macros.disk import (
    cd, link_safely, make_folder, COMMAND_LINE_HOME,
    HOME_FOLDER)
from invisibleroads_macros.iterable import merge_dictionaries
from invisibleroads_macros.text import unicode_safely
from os.path import abspath, basename, exists, isabs, join
from stevedore.extension import ExtensionManager

from ..configurations import (
    ResultConfiguration, find_tool_definition, load_result_arguments,
    load_tool_definition, parse_data_dictionary, render_command)
from ..exceptions import CrossComputeError, DataParseError
from ..extensions import DefaultTool
from ..models import Tool
from ..symmetries import subprocess, ENVIRONMENT_VARIABLES
from ..types import initialize_data_types


class ToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument(
            'tool_name', nargs='?', type=unicode_safely, default='')
        argument_subparser.add_argument(
            '--data_folder', metavar='FOLDER', type=unicode_safely)
        argument_subparser.add_argument(
            '--suffix_by_data_type', metavar='JSON', type=json.loads)
        argument_subparser.add_argument(
            '--with_debugging', action='store_true')

    def run(self, args):
        logging.basicConfig(level=logging.WARNING)
        initialize_data_types(args.suffix_by_data_type)
        tool_definition = prepare_tool_definition(
            args.tool_name, args.with_debugging)
        tool_name = tool_definition['tool_name']
        data_folder = args.data_folder or join(
            HOME_FOLDER, '.crosscompute', tool_name)
        tool_folder = Tool().get_folder(data_folder)
        link_safely(tool_folder, tool_definition['configuration_folder'])
        tool_definition = find_tool_definition(tool_folder, tool_name)
        tool_definition['tool_name'] = tool_name
        return tool_definition, data_folder


def launch(argv=sys.argv):
    argument_parser = StoicArgumentParser('crosscompute', add_help=False)
    argument_subparsers = argument_parser.add_subparsers(dest='command')
    scripts_by_name = get_scripts_by_name('crosscompute')
    configure_subparsers(argument_subparsers, scripts_by_name)
    args = argument_parser.parse_known_args(argv[1:])[0]
    run_scripts(scripts_by_name, args)


def prepare_tool_definition(tool_name, with_debugging=False):
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
            tool_name, with_debugging)
    except CrossComputeError as e:
        exit(e)
    return tool_definition


def corral_arguments(argument_folder, result_arguments, use=link_safely):
    d = result_arguments.copy()
    make_folder(argument_folder)
    for k, v in result_arguments.items():
        if not k.endswith('_path'):
            continue
        assert isabs(v)
        try:
            d[k] = use(join(argument_folder, basename(v)), v)
        except IOError as e:
            raise IOError(k, v)
    return d


def run_script(
        tool_definition, result_arguments, result_folder, target_folder=None,
        environment=None, without_logging=False, external_folders=None):
    timestamp, environment = time.time(), environment or {}
    if 'target_folder' in tool_definition['argument_names']:
        y = make_folder(abspath(target_folder or join(result_folder, 'y')))
        result_arguments = OrderedDict(result_arguments, target_folder=y)
    # Record
    result_configuration = ResultConfiguration(result_folder, without_logging)
    result_configuration.save_tool_location(tool_definition)
    result_configuration.save_result_scripts(tool_definition, result_arguments)
    result_configuration.save_result_arguments(
        tool_definition, result_arguments, environment, external_folders)
    # Run
    command_terms = split_arguments(render_command(tool_definition[
        'command_template'].replace('\n', ' '), result_arguments))
    result_properties = OrderedDict()
    output_file = open(join(result_folder, 'f.log'), 'w+t')
    try:
        with cd(tool_definition['configuration_folder']):
            return_code = subprocess.call(
                command_terms,
                stdout=output_file,
                stderr=subprocess.STDOUT,
                env=merge_dictionaries(environment, ENVIRONMENT_VARIABLES))
    except OSError:
        output_file.write('Command not found')
    else:
        if return_code:
            result_properties['return_code'] = return_code
    # Save
    result_properties.update(_process_output(
        output_file, result_folder, tool_definition, without_logging))
    result_properties['execution_time_in_seconds'] = time.time() - timestamp
    result_configuration.save_result_properties(result_properties)
    if 'target_folder' in tool_definition['argument_names']:
        link_safely(join(
            result_folder, 'y'), result_arguments['target_folder'])
    return result_properties


def _process_output(
        output_file, result_folder, tool_definition, without_logging=False):
    d, type_errors = OrderedDict(), OrderedDict()
    output_file.seek(0)
    output_content = unicode_safely(output_file.read().strip())
    if output_content:
        output_content = output_content.replace(HOME_FOLDER, COMMAND_LINE_HOME)
        if not without_logging:
            print(SECTION_TEMPLATE % ('raw_output', output_content))
        try:
            value_by_key = parse_data_dictionary(
                output_content, join(result_folder, 'y'), external_folders=[])
        except DataParseError as e:
            for k, v in e.message_by_name.items():
                type_errors['%s.error' % k] = v
            value_by_key = e.value_by_key
        if tool_definition.get('show_raw_output'):
            d['raw_output'] = output_content
        if value_by_key:
            d['raw_outputs'] = _filter_outputs(
                value_by_key, tool_definition.get('ignored_outputs', []))
    if type_errors:
        d['type_errors'] = type_errors
    return d


def _filter_outputs(value_by_key, target_expressions):
    d = OrderedDict()
    for k, v in value_by_key.items():
        if any(fnmatch(k, x) for x in target_expressions):
            continue
        d[k] = v
    return d

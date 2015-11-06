import codecs
import os
import re
import shlex
import subprocess
import sys
import time
from collections import OrderedDict
from os.path import dirname, join, relpath
from invisibleroads.scripts import (
    ReflectiveArgumentParser,
    configure_subparsers, get_scripts_by_name, run_scripts)
from invisibleroads_macros.disk import cd
from invisibleroads_macros.exceptions import InvisibleRoadsError
from invisibleroads_macros.log import (
    format_hanging_indent, format_path, format_summary, sort_dictionary,
    stylize_dictionary)
from invisibleroads_repositories import (
    get_github_repository_commit_hash, get_github_repository_url)

from ..configurations import get_tool_definition
from ..exceptions import CrossComputeError
from ..types import format_data_dictionary, parse_data_dictionary


class _ResultConfiguration(object):

    def __init__(self, target_folder):
        self.target_file = open(join(target_folder, 'result.cfg'), 'wt')

    def write_header(self, tool_definition, result_arguments):
        target_folder = result_arguments['target_folder']
        tool_argument_names = list(tool_definition['argument_names'])
        try:
            tool_argument_names.remove('target_folder')
        except ValueError:
            pass
        # Write tool_definition
        template = '[tool_definition]\n%s\n'
        tool_definition = stylize_tool_definition(
            tool_definition, result_arguments)
        print(template % format_summary(
            sort_dictionary(tool_definition, [
                'repository_url', 'tool_name', 'commit_hash',
                'configuration_path', 'command',
            ]), [
                ('command', format_hanging_indent),
            ]))
        self.target_file.write(template % format_summary(
            sort_dictionary(tool_definition, [
                'repository_url', 'tool_name', 'commit_hash',
            ])) + '\n')
        # Write result_arguments
        template = '[result_arguments]\n%s\n'
        result_arguments = sort_dictionary(
            result_arguments, tool_argument_names)
        print(template % format_summary(
            OrderedDict(result_arguments, target_folder=target_folder)))
        self.target_file.write(template % format_summary(
            result_arguments) + '\n')

    def write_footer(self, result_properties, data_type_packs):
        template = '[result_properties]\n%s'
        result_properties.pop('_standard_output', None)
        result_properties.pop('_standard_error', None)
        print(template % format_data_dictionary(
            result_properties, data_type_packs, censored=False))
        self.target_file.write(template % format_data_dictionary(
            result_properties, data_type_packs, censored=True) + '\n')


def launch(argv=sys.argv):
    argument_parser = ReflectiveArgumentParser(
        'crosscompute', add_help=False)
    argument_subparsers = argument_parser.add_subparsers(dest='command')
    scripts_by_name = get_scripts_by_name('crosscompute')
    configure_subparsers(argument_subparsers, scripts_by_name)
    args = argument_parser.parse_known_args(argv[1:])[0]
    run_scripts(scripts_by_name, args)


def load_tool_definition(tool_name):
    try:
        tool_definition = get_tool_definition(tool_name=tool_name)
    except CrossComputeError as e:
        sys.exit(e)
    return tool_definition


def stylize_tool_definition(tool_definition, result_arguments):
    d = {
        'tool_name': tool_definition['tool_name'],
        'configuration_path': relpath(tool_definition['configuration_path']),
    }
    tool_folder = dirname(tool_definition['configuration_path'])
    try:
        d['repository_url'] = get_github_repository_url(tool_folder)
        d['commit_hash'] = get_github_repository_commit_hash(tool_folder)
    except InvisibleRoadsError:
        pass
    d['command'] = render_command(
        tool_definition['command_template'],
        **stylize_dictionary(result_arguments, [
            ('_folder', format_path),
            ('_path', format_path),
        ]))
    return d


def run_script(
        target_folder, tool_definition, result_arguments, data_type_packs,
        save_logs=False, debug=False):
    result_properties, timestamp = OrderedDict(), time.time()
    result_arguments = dict(result_arguments, target_folder=target_folder)
    result_configuration = _ResultConfiguration(target_folder)
    result_configuration.write_header(tool_definition, result_arguments)
    command = render_command(
        tool_definition['command_template'], result_arguments)
    try:
        with cd(dirname(tool_definition['configuration_path'])):
            command_process = subprocess.Popen(
                shlex.split(command, posix=os.name == 'posix'),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        standard_output, standard_error = [codecs.getdecoder('unicode_escape')(
            x.rstrip())[0] for x in command_process.communicate()]
        if command_process.returncode:
            result_properties['return_code'] = command_process.returncode
    except OSError:
        standard_output, standard_error = None, 'Command not found'
    for stream_name, stream_content in [
        ('standard_output', standard_output),
        ('standard_error', standard_error),
    ]:
        _store_stream(
            target_folder, stream_name, stream_content, tool_definition,
            result_properties, data_type_packs, save_logs)
    result_properties['execution_time_in_seconds'] = time.time() - timestamp
    result_configuration.write_footer(result_properties, data_type_packs)
    if debug and standard_error:
        print('\n' + standard_error)
    return result_properties


def render_command(command_template, result_arguments):
    d = {}
    quote_pattern = re.compile(r"""["'].*["']""")
    for k, v in result_arguments.items():
        v = v.strip()
        if ' ' in v and not quote_pattern.match(v):
            v = '"%s"' % v
        d[k] = v
    return command_template.format(**d)


def _store_stream(
        target_folder, target_nickname, stream_content, tool_definition,
        result_properties, data_type_packs, write_to_disk):
    if not stream_content:
        return
    key_prefix = '' if tool_definition.get('show_' + target_nickname) else '_'
    result_properties[key_prefix + target_nickname] = stream_content
    if write_to_disk:
        target_path = join(target_folder, '%s.log' % target_nickname)
        open(target_path, 'wt').write(stream_content + '\n')
    value_by_key = parse_data_dictionary(stream_content, data_type_packs)
    if value_by_key:
        result_properties[target_nickname + 's'] = value_by_key

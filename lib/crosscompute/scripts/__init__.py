import shlex
import subprocess
import sys
import time
from collections import OrderedDict
from os.path import dirname, join, relpath
from invisibleroads_macros.disk import cd
from invisibleroads_macros.exceptions import InvisibleRoadsError
from invisibleroads_macros.log import (
    format_hanging_indent, format_nested_dictionary, format_path,
    sort_dictionary, stylize_dictionary)
from invisibleroads_repositories import (
    get_github_repository_commit_hash, get_github_repository_url)

from ..configurations import get_tool_definition
from ..exceptions import CrossComputeError
from ..types import parse_data_dictionary


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
        suffix_format_packs = [
            ('command', format_hanging_indent),
            ('_path', format_path),
        ]
        print(template % format_nested_dictionary(
            sort_dictionary(tool_definition, [
                'repository_url', 'tool_name', 'commit_hash',
                'configuration_path', 'command',
            ]), suffix_format_packs))
        self.target_file.write(template % format_nested_dictionary(
            sort_dictionary(tool_definition, [
                'repository_url', 'tool_name', 'commit_hash',
            ])) + '\n')
        # Write result_arguments
        template = '[result_arguments]\n%s\n'
        result_arguments = sort_dictionary(
            result_arguments, tool_argument_names)
        suffix_format_packs = [
            ('_folder', format_path),
            ('_path', format_path),
        ]
        print(template % format_nested_dictionary(
            OrderedDict(result_arguments, target_folder=target_folder),
            suffix_format_packs))
        self.target_file.write(template % format_nested_dictionary(
            result_arguments, suffix_format_packs) + '\n')

    def write_footer(self, result_properties, data_type_packs):
        template = '[result_properties]\n%s'
        suffix_format_packs = [
            (suffix, data_type.format) for suffix, data_type in data_type_packs
        ] + [
            ('_folder', format_path),
            ('_path', format_path),
        ]
        result_properties.pop('_standard_output', None)
        result_properties.pop('_standard_error', None)
        print(template % format_nested_dictionary(
            result_properties, suffix_format_packs, censored=False))
        self.target_file.write(template % format_nested_dictionary(
            result_properties, suffix_format_packs, censored=True) + '\n')


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
    d['command'] = tool_definition['command_template'].format(
        **stylize_dictionary(result_arguments, [
            ('_folder', format_path),
            ('_path', format_path)]))
    return d


def run_script(
        target_folder, tool_definition, result_arguments, data_type_packs,
        save_logs=False):
    timestamp = time.time()
    result_arguments = dict(result_arguments, target_folder=target_folder)
    result_configuration = _ResultConfiguration(target_folder)
    result_configuration.write_header(tool_definition, result_arguments)
    command = tool_definition['command_template'].format(**result_arguments)
    with cd(dirname(tool_definition['configuration_path'])):
        command_process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    standard_output, standard_error = [
        x.rstrip() for x in command_process.communicate()]
    result_properties = OrderedDict()
    if standard_output:
        key_prefix = '' if tool_definition.get('show_standard_output') else '_'
        result_properties[key_prefix + 'standard_output'] = standard_output
        if save_logs:
            _save_log(target_folder, 'standard_output', standard_output)
    if standard_error:
        key_prefix = '' if tool_definition.get('show_standard_error') else '_'
        result_properties[key_prefix + 'standard_error'] = standard_error
        if save_logs:
            _save_log(target_folder, 'standard_error', standard_error)
    standard_outputs = parse_data_dictionary(standard_output, data_type_packs)
    if standard_outputs:
        result_properties['standard_outputs'] = standard_outputs
    standard_errors = parse_data_dictionary(standard_error, data_type_packs)
    if standard_errors:
        result_properties['standard_errors'] = standard_errors
    result_properties['execution_time_in_seconds'] = time.time() - timestamp
    result_configuration.write_footer(result_properties, data_type_packs)
    return result_properties


def _save_log(target_folder, target_nickname, text):
    target_path = join(target_folder, '%s.log' % target_nickname)
    target_file = open(target_path, 'wt')
    target_file.write(text + '\n')

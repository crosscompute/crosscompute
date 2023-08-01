# TODO: Consider sanitize_json_value for result input, output, log, debug

import json
import re
import requests
import time
from collections import defaultdict
from concurrent.futures import (
    ThreadPoolExecutor)
from copy import deepcopy
from io import StringIO
from sys import exc_info
from traceback import print_exception

from .connection import (
    fetch_resource,
    get_bash_configuration_text,
    get_token,
    yield_echo)
from .definition import (
    get_nested_value,
    get_variable_dictionary_by_id)
from .serialization import (
    define_save,
    render_object,
    save_json)
from ..exceptions import (
    CrossComputeConnectionError,
    CrossComputeDefinitionError,
    CrossComputeError,
    CrossComputeExecutionError,
    CrossComputeImplementationError,
    CrossComputeKeyboardInterrupt)
from ..macros import (
    sanitize_name,
    sanitize_json_value)
from ..symmetries import download


# https://stackoverflow.com/a/14693789/192092
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def run_report(enumerated_report_dictionary, style_rules, log=None, save=None):
    report_index, report_dictionary = enumerated_report_dictionary
    variable_dictionaries = get_nested_value(
        report_dictionary, 'input', 'variables', [])
    template_dictionaries = get_nested_value(
        report_dictionary, 'output', 'templates', [])
    report_name = get_result_name(report_dictionary)
    log and log({'index': [
        report_index], 'status': 'RUNNING', 'name': report_name})
    with ThreadPoolExecutor() as executor:
        document_block_packs = executor.map(
            run_template,
            enumerate(template_dictionaries),
            repeat(variable_dictionaries),
            repeat(report_index),
            repeat(log))
    document_blocks = []
    for blocks in document_block_packs:
        document_blocks.extend(blocks)
    if document_blocks:
        document_blocks.pop()
    log and log({'index': [
        report_index], 'status': 'DONE', 'name': report_name})
    document_dictionary = {
        'name': report_name,
        'blocks': document_blocks,
        'styles': style_rules,
        'header': get_nested_value(report_dictionary, 'print', 'header', ''),
        'footer': get_nested_value(report_dictionary, 'print', 'footer', ''),
    }
    save and save(report_index, document_dictionary)
    return document_dictionary


def run_worker(
        script_command=None, with_tests=True, is_quiet=False, as_json=False):
    # TODO: Use token to determine the worker type
    tool_definition = fetch_resource('tools', get_token())
    if not is_quiet:
        print(render_object(tool_definition, as_json))
    if with_tests:
        test_summary = run_tests(tool_definition)
        if not is_quiet:
            print(render_object(test_summary, as_json))
    d = defaultdict(int)
    while True:
        try:
            for [
                event_name, event_dictionary,
            ] in yield_echo(d, is_quiet, as_json):
                if event_name == 'i' or d['ping count'] % 100 == 0:
                    d['result count'] += process_result_input_stream(
                        script_command, is_quiet, as_json)
        except CrossComputeKeyboardInterrupt:
            break
        except (
            CrossComputeConnectionError,
            requests.exceptions.HTTPError,
        ) as e:
            print(e)
            time.sleep(1)
        except Exception:
            print_exception(*exc_info())
            time.sleep(1)
    if not is_quiet and not as_json:
        print('\n' + get_bash_configuration_text())
        print('cd ' + getcwd())
        print('crosscompute workers run')
    return dict(d)


def run_tests(tool_definition):
    tool_definition_folder = tool_definition.get('folder', '.')
    input_variable_definitions = tool_definition['input']['variables']
    test_dictionaries = tool_definition['tests']
    error_by_folder = {}
    result_dictionaries = []
    for test_dictionary in test_dictionaries:
        relative_folder = test_dictionary['folder']
        test_folder = join(tool_definition_folder, relative_folder)
        input_folder = join(test_folder, 'input')
        try:
            input_variable_dictionaries = process_variable_folder(
                input_folder, input_variable_definitions)
            result_dictionary = {'input': {
                'variables': input_variable_dictionaries}}
            result_dictionary = run_tool(tool_definition, result_dictionary)
        except CrossComputeError as e:
            error_by_folder[relative_folder] = e.args[0]
            continue
        result_dictionaries.append(result_dictionary)
    test_count = len(test_dictionaries)
    d = {
        'tests total count': test_count,
        'tests passed count': test_count - len(error_by_folder),
    }
    if error_by_folder:
        d['error by folder'] = error_by_folder
        raise CrossComputeExecutionError(d)
    d['results'] = result_dictionaries
    return d


def prepare_variable_folder(
        folder, variable_definitions, variable_dictionaries):
        if 'dataset' in variable_data:
            if not exists(file_path):
                dataset_dictionary = variable_data['dataset']
                dataset_id = dataset_dictionary['id']
                dataset_version_id = dataset_dictionary['version']['id']
                d = fetch_resource(
                    'datasets', dataset_id + '/versions/' + dataset_version_id)
                download(d['file']['url'], file_path)
            continue
        if 'file' in variable_data:
            if not exists(file_path):
                file_id = variable_data['file']['id']
                d = fetch_resource('files', file_id)
                download(d['url'], file_path)
            continue
        if 'value' not in variable_data:
            continue


def process_result_input_stream(script_command, is_quiet, as_json):
    result_count = 0
    while True:
        chore_dictionary = fetch_resource('chores')
        if not chore_dictionary:
            break
        if not is_quiet:
            print('{', end='', flush=True)
        # TODO: Get tool script from cloud
        tool_definition = chore_dictionary['tool']
        result_dictionary = chore_dictionary['result']
        result_token = result_dictionary['token']
        try:
            result_dictionary = run_tool(
                tool_definition, result_dictionary, script_command)
        except CrossComputeError as e:
            if not is_quiet:
                print(render_object(e.args[0], as_json))
            result_progress = -1
        else:
            result_progress = 100
        result_dictionary = process_result_definition(
            result_dictionary, tool_definition, prepare_dataset)
        result_dictionary['progress'] = result_progress
        if not is_quiet:
            print('}', end='', flush=True)
        fetch_resource(
            'results', result_dictionary['id'], method='PATCH',
            data=result_dictionary, token=result_token)
        result_count += 1
    return result_count


def get_result_name(result_dictionary):
    result_name = raw_result_name.format_map(SafeDict(variable_value_by_id))
    return sanitize_name(result_name)


def clean_bash_output(output_file):
    output_file.seek(0)
    # TODO: Render ansi escape codes in jupyter error dialog
    return ANSI_ESCAPE_PATTERN.sub('', output_file.read())

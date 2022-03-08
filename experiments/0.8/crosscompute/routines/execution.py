# TODO: Consider sanitize_json_value for result input, output, log, debug

import json
import re
import requests
import subprocess
import time
from collections import defaultdict
from concurrent.futures import (
    ThreadPoolExecutor)
from copy import deepcopy
from functools import partial
from invisibleroads_macros_disk import (
    TemporaryStorage, make_folder, make_random_folder)
from io import StringIO
from itertools import product, repeat
from mimetypes import guess_type
from os import environ, getcwd
from os.path import (
    abspath, basename, dirname, getsize, exists, isdir, join, splitext)
from sys import exc_info
from traceback import print_exception

from .connection import (
    fetch_resource,
    get_bash_configuration_text,
    get_token,
    yield_echo)
from .definition import (
    get_nested_value,
    get_template_dictionary,
    get_variable_dictionary_by_id,
    load_definition)
from .serialization import (
    define_load,
    define_save,
    load_value_json,
    render_object,
    save_json,
    SAVE_BY_EXTENSION_BY_VIEW)
from ..constants import DEBUG_VARIABLE_DEFINITIONS, S
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


def run_report_automation(report_definition, is_mock=True, log=None):
    style_dictionary = get_nested_value(
        report_definition, 'print', 'style', {})
    style_rules = style_dictionary.get('rules', [])
    if not is_mock:
        response_json = fetch_resource('prints', method='POST')
        print_id = response_json['id']
    else:
        print_id = None

    def save(document_index, document_dictionary):
        if not is_mock:
            fetch_resource(
                'prints', f'{print_id}/documents/{document_index}',
                method='PUT', data=document_dictionary)
        return document_dictionary

    with ThreadPoolExecutor() as executor:
        document_dictionaries = executor.map(
            run_report,
            enumerate(yield_result_dictionary(report_definition)),
            repeat(style_rules),
            repeat(log),
            repeat(save))
    document_dictionaries = list(document_dictionaries)
    document_count = len(document_dictionaries)
    d = {'documents': document_dictionaries}
    if not is_mock:
        response_json = fetch_resource(
            'prints', print_id, method='PATCH', data={'count': document_count})
        d['url'] = response_json['url']
    return d


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


def run_template(
        enumerated_template_dictionary,
        variable_dictionaries,
        report_index,
        log):
    document_blocks = []
    template_index, template_dictionary = enumerated_template_dictionary
    template_kind = template_dictionary.get('kind')
    if template_kind == 'result':
        result_dictionary = deepcopy(template_dictionary)
        tool_definition = result_dictionary.pop('tool')
        old_variable_dictionary_by_id = get_variable_dictionary_by_id(
            get_nested_value(result_dictionary, 'input', 'variables'))
        new_variable_dictionary_by_id = get_variable_dictionary_by_id(
            variable_dictionaries)
        variable_dictionary_by_id = {
            **old_variable_dictionary_by_id,
            **new_variable_dictionary_by_id}
        variable_dictionaries = variable_dictionary_by_id.values()
        result_dictionary['input']['variables'] = variable_dictionaries
        result_name = get_result_name(result_dictionary)
        log and log({'index': [
            report_index, template_index,
        ], 'status': 'RUNNING', 'name': result_name})
        try:
            result_dictionary = run_tool(tool_definition, result_dictionary)
        except CrossComputeError:
            log and log({'index': [
                report_index, template_index], 'status': 'ERROR'})
            raise
        document_dictionary = render_result(
            tool_definition, result_dictionary)
        result_name = get_result_name(result_dictionary)  # Recompute
        log and log({'index': [
            report_index, template_index,
        ], 'status': 'DONE', 'name': result_name})
        document_blocks.extend(document_dictionary.get('blocks', []))
        # TODO: Replace this with article wrappers
        document_blocks.append({
            'view': 'markdown',
            'data': {'value': '<div style="page-break-after: always;" />'},
        })
    elif template_kind == 'report':
        raise CrossComputeImplementationError({
            'template': 'does not yet support report definitions'})
    elif 'blocks' in template_dictionary:
        raise CrossComputeImplementationError({
            'template': 'does not yet support report blocks'})
    return document_blocks


def run_result_automation(result_definition, is_mock=True, log=None):
    if not is_mock:
        response_json = fetch_resource('prints', method='POST')
        print_id = response_json['id']
    else:
        print_id = None

    def save(document_index, document_dictionary):
        if not is_mock:
            fetch_resource(
                'prints', f'{print_id}/documents/{document_index}',
                method='PUT', data=document_dictionary)
        return document_dictionary

    with ThreadPoolExecutor() as executor:
        document_dictionaries = executor.map(
            run_result,
            enumerate(yield_result_dictionary(result_definition)),
            repeat(log),
            repeat(save))
    document_dictionaries = list(document_dictionaries)
    document_count = len(document_dictionaries)
    d = {'documents': document_dictionaries}
    if not is_mock:
        response_json = fetch_resource('prints', print_id, method='PATCH', data={
            'count': document_count})
        d['url'] = response_json['url']
    return d


def run_result(enumerated_result_dictionary, log=None, save=None):
    result_index, result_dictionary = enumerated_result_dictionary
    result_name = get_result_name(result_dictionary)
    log and log({'index': [
        result_index,
    ], 'status': 'RUNNING', 'name': result_name})
    tool_definition = result_dictionary.pop('tool')
    try:
        result_dictionary = run_tool(tool_definition, result_dictionary)
    except CrossComputeError:
        log and log({'index': [result_index], 'status': 'ERROR'})
        raise
    document_dictionary = render_result(tool_definition, result_dictionary)
    result_name = get_result_name(result_dictionary)  # Recompute
    log and log({'index': [
        result_index,
    ], 'status': 'DONE', 'name': result_name})
    save and save(result_index, document_dictionary)
    return document_dictionary


def run_tool(tool_definition, result_dictionary, script_command=None):
    if not script_command:
        script_command = tool_definition['script']['command']
    script_folder = join(tool_definition.get(
        'folder', '.'), tool_definition['script']['folder'])
    result_folder = get_result_folder(result_dictionary)
    folder_by_name = {k: make_folder(join(result_folder, k)) for k in [
        'input', 'output', 'log', 'debug']}
    folder_by_key = {k + '_folder': v for k, v in folder_by_name.items()}
    prepare_variable_folder(
        folder_by_name['input'], tool_definition['input']['variables'],
        result_dictionary['input']['variables'])
    script_environment = get_script_environment(tool_definition.get(
        'environment', {}).get('variables', []), folder_by_key)
    run_script(script_command.format(
        **folder_by_key), script_folder, script_environment)
    for folder_name in 'output', 'log', 'debug':
        variable_definitions = list(get_nested_value(
            tool_definition, folder_name, 'variables', []))
        if folder_name == 'debug':
            variable_definitions += DEBUG_VARIABLE_DEFINITIONS
        if not variable_definitions:
            continue
        result_dictionary[folder_name] = {
            'variables': process_variable_folder(folder_by_name[
                folder_name], variable_definitions)}
    if 'name' in result_dictionary:
        result_dictionary['name'] = get_result_name(result_dictionary)
    return result_dictionary


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


def run_script(script_command, script_folder, script_environment):
    debug_folder = script_environment.get('CROSSCOMPUTE_DEBUG_FOLDER', '')
    stdout_file = open(join(debug_folder, 'stdout.txt'), 'w+t')
    stderr_file = open(join(debug_folder, 'stderr.txt'), 'w+t')
    try:
        subprocess.run(
            script_command, env=script_environment, cwd=script_folder,
            stdout=stdout_file, stderr=stderr_file, encoding='utf-8',
            shell=True, check=True)
    except FileNotFoundError:
        raise CrossComputeDefinitionError({
            'script': 'could not run command ' + script_command})
    except subprocess.CalledProcessError:
        raise CrossComputeExecutionError({
            'stdout': clean_bash_output(stdout_file),
            'stderr': clean_bash_output(stderr_file)})
    stdout_file.close()
    stderr_file.close()


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


def yield_result_dictionary(result_definition):
    variable_ids = []
    variable_data_lists = []
    for variable_dictionary in get_nested_value(result_definition, 'input', 'variables'):
        variable_id = variable_dictionary['id']
        if 'data' not in variable_dictionary:
            continue
        variable_data = variable_dictionary['data']
        if not isinstance(variable_data, list):
            continue
        variable_ids.append(variable_id)
        variable_data_lists.append(variable_data)
    for variable_data_selection in product(*variable_data_lists):
        result_dictionary = deepcopy(result_definition)
        selected_data_by_id = dict(zip(variable_ids, variable_data_selection))

        def update(variable_dictionary):
            variable_id = variable_dictionary['id']
            if variable_id in selected_data_by_id:
                variable_dictionary['data'] = selected_data_by_id[variable_id]
            return variable_dictionary

        result_dictionary['input']['variables'] = [update(
            _) for _ in result_dictionary['input']['variables']]
        yield result_dictionary


def prepare_dataset(file_path, file_view, project_dictionaries):
    mime_type = get_mime_type(file_path)
    dataset_dictionary = fetch_resource('datasets', method='POST', data={
        'name': basename(file_path),
        'view': file_view,
        'type': mime_type,
        'size': getsize(file_path),
        'projects': project_dictionaries,
    })
    dataset_id = dataset_dictionary['id']
    dataset_version_id = dataset_dictionary['version']['id']
    file_dictionary = dataset_dictionary['file']
    file_id = file_dictionary['id']
    file_url = file_dictionary['url']
    file_object = open(file_path, 'rb')
    if file_path.endswith('json'):
        d = sanitize_json_value(json.load(file_object))
        file_object = StringIO(json.dumps(d))
    requests.put(file_url, data=file_object)
    fetch_resource('files', file_id, method='PATCH')
    return {'id': dataset_id, 'version': {'id': dataset_version_id}}


def prepare_variable_folder(
        folder, variable_definitions, variable_dictionaries):
    value_by_id_by_path = defaultdict(dict)
    variable_data_by_id = get_data_by_id(variable_dictionaries)
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        try:
            variable_data = variable_data_by_id[variable_id]
        except KeyError:
            raise CrossComputeDefinitionError({
                'variable': f'could not find data for {variable_id}'})
        file_path = join(folder, variable_definition['path'])
        make_folder(dirname(file_path))
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
        variable_value = variable_data['value']
        variable_view = variable_definition['view']
        file_extension = splitext(file_path)[1]
        save = define_save(variable_view, file_extension)
        try:
            save(file_path, variable_value, variable_id, value_by_id_by_path)
        except ValueError:
            raise CrossComputeExecutionError({
                'path': 'is unsaveable by view ' + variable_view + file_path})
        except CrossComputeError:
            raise
        except Exception:
            print_exception(*exc_info())
            raise CrossComputeImplementationError({'path': 'triggered an exception'})
    for file_path, value_by_id in value_by_id_by_path.items():
        file_extension = splitext(file_path)[1]
        if file_extension == '.json':
            save_json(file_path, value_by_id)


def process_variable_folder(folder, variable_definitions):
    load_value_json.cache_clear()
    variable_dictionaries = []
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        variable_path = variable_definition['path']
        variable_view = variable_definition['view']
        file_extension = splitext(variable_path)[1]
        file_path = join(folder, variable_path)
        load = define_load(variable_view, file_extension)
        try:
            variable_value = load(file_path, variable_id)
        except OSError:
            raise CrossComputeDefinitionError({'path': 'is bad ' + file_path})
        except (ValueError, UnicodeDecodeError):
            raise CrossComputeExecutionError({
                'path': 'is unloadable by view ' + variable_view + file_path})
        except CrossComputeError:
            raise
        except Exception:
            print_exception(*exc_info())
            raise CrossComputeImplementationError({'path': 'triggered an exception'})
        variable_dictionaries.append({
            'id': variable_id, 'data': {'value': variable_value}})
    return variable_dictionaries


def process_variable_dictionary(
        variable_dictionary, variable_definition, prepare_dataset):
    variable_view = variable_definition['view']
    variable_data = variable_dictionary['data']
    if 'value' not in variable_data:
        return variable_dictionary
    variable_value = variable_data['value']
    variable_value_length = len(repr(variable_value))
    if variable_view in [
        'text',
        'number',
        'markdown',
    ] and variable_value_length < S['maximum_variable_value_length']:
        return variable_dictionary
    variable_id = variable_definition['id']
    file_extension, save = list(SAVE_BY_EXTENSION_BY_VIEW[
        variable_view].items())[0]
    file_name = f'{variable_id}{file_extension}'
    with TemporaryStorage() as storage:
        file_path = join(storage.folder, file_name)
        save(file_path, variable_value, variable_id, {})
        dataset_dictionary = prepare_dataset(file_path, variable_view)
    dataset_id = dataset_dictionary['id']
    dataset_version_id = dataset_dictionary['version']['id']
    variable_dictionary['data'] = {'dataset': {
        'id': dataset_id, 'version': {'id': dataset_version_id}}}
    return variable_dictionary


def process_result_definition(
        result_dictionary, tool_definition, prepare_dataset):
    prepare_dataset = partial(
        prepare_dataset,
        project_dictionaries=result_dictionary.get('projects', []))
    for key in 'input', 'output', 'log', 'debug':
        variable_dictionaries = get_nested_value(
            result_dictionary, key, 'variables', [])
        variable_definitions = get_nested_value(
            tool_definition, key, 'variables', [])

        variable_dictionary_by_id = {
            _['id']: _ for _ in variable_dictionaries}
        if not variable_dictionary_by_id:
            continue

        for variable_definition in variable_definitions:
            variable_id = variable_definition['id']
            variable_dictionary = variable_dictionary_by_id[variable_id]
            process_variable_dictionary(
                variable_dictionary, variable_definition, prepare_dataset)
    return result_dictionary


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
    variable_value_by_id = {}
    for key in ['input', 'output']:
        if key not in result_dictionary:
            continue
        put_dictionary = result_dictionary[key]
        if 'variables' not in put_dictionary:
            continue
        for variable_definition in put_dictionary['variables']:
            try:
                variable_id = variable_definition['id']
                variable_data = variable_definition['data']
                if type(variable_data) is not dict:
                    raise CrossComputeExecutionError({'definition': f'{variable_id} has a bad structure, it couldn\'t be batch'})

                variable_value = variable_data['value']
            except KeyError:
                continue
            if type(variable_value) not in [int, float, str]:
                continue
            variable_value_by_id[variable_id] = variable_value
    raw_result_name = result_dictionary['name']
    result_name = raw_result_name.format_map(SafeDict(variable_value_by_id))
    return sanitize_name(result_name)


def clean_bash_output(output_file):
    output_file.seek(0)
    # TODO: Render ansi escape codes in jupyter error dialog
    return ANSI_ESCAPE_PATTERN.sub('', output_file.read())

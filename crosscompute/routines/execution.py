import re
import shlex
import subprocess
from collections import defaultdict
from copy import deepcopy
from invisibleroads_macros_disk import make_folder, make_random_folder
from itertools import chain, product
from os import environ, getcwd
from os.path import abspath, dirname, exists, isdir, join, splitext
from pyramid.httpexceptions import HTTPInternalServerError
from subprocess import CalledProcessError
from sys import exc_info
from traceback import print_exception

from .connection import (
    get_bash_configuration_text,
    fetch_resource,
    get_echoes_client,
    get_token)
from .definition import (
    get_template_dictionary,
    load_definition)
from .serialization import (
    load_value_json,
    render_object,
    save_json,
    LOAD_BY_EXTENSION_BY_VIEW,
    SAVE_BY_EXTENSION_BY_VIEW)
from ..constants import DEBUG_VARIABLE_DEFINITIONS, S
from ..exceptions import (
    CrossComputeDefinitionError,
    CrossComputeError,
    CrossComputeExecutionError,
    CrossComputeImplementationError)


# https://stackoverflow.com/a/14693789/192092
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class SafeDict(dict):
    # https://stackoverflow.com/a/17215533/192092

    def __missing__(self, key):
        return '{' + key + '}'


def run_automation(automation_definition, is_mock):
    automation_kind = automation_definition['kind']
    if automation_kind == 'result':
        d = run_result_automation(automation_definition, is_mock)
    elif automation_kind == 'report':
        raise CrossComputeImplementationError({
            'report': 'has not been implemented yet'})
    return d


def run_result_automation(result_definition, is_mock=True):
    document_dictionaries = []
    for result_dictionary in yield_result_dictionary(result_definition):
        tool_definition = result_dictionary.pop('tool')
        result_dictionary = run_tool(tool_definition, result_dictionary)
        document_dictionary = render_result(tool_definition, result_dictionary)
        document_dictionaries.append(document_dictionary)
    d = {
        'documents': document_dictionaries,
    }
    if not is_mock:
        response_json = fetch_resource('prints', method='POST', data=d)
        d['url'] = response_json['url']
    return d


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
    run_script(script_command.format(
        **folder_by_key), script_folder, **folder_by_key)
    for folder_name in 'output', 'log', 'debug':
        if folder_name not in tool_definition:
            continue
        variable_definitions = tool_definition[folder_name]['variables']
        if folder_name == 'debug':
            variable_definitions += DEBUG_VARIABLE_DEFINITIONS
        result_dictionary[folder_name] = {
            'variables': process_variable_folder(folder_by_name[
                folder_name], variable_definitions)}
    if 'name' in result_dictionary:
        result_dictionary['name'] = get_result_name(result_dictionary)
    return result_dictionary


def run_worker(script_command=None, is_quiet=False, as_json=False):
    # TODO: Make generalizable worker wrapper
    tool_definition = fetch_resource('tools', get_token())
    if not is_quiet:
        print(render_object(tool_definition, as_json))
    test_summary = run_tests(tool_definition)
    if not is_quiet:
        print(render_object(test_summary, as_json))
    worker_dictionary = defaultdict(int)
    try:
        for echo_message in get_echoes_client():
            event_name = echo_message.event
            if event_name == 'message':
                if not is_quiet and not as_json:
                    print('.', end='', flush=True)
                worker_dictionary['ping count'] += 1
            elif not is_quiet:
                print('\n' + render_object(echo_message.__dict__, as_json))
            is_bored = worker_dictionary['ping count'] % 100 == 0
            if event_name == 'i' or is_bored:
                worker_dictionary['result count'] += process_result_input_stream(
                    script_command, is_quiet, as_json)
    except KeyboardInterrupt:
        pass
    if not is_quiet and not as_json:
        print('\n' + get_bash_configuration_text())
        print('cd ' + getcwd())
        print('crosscompute workers run')
    return dict(worker_dictionary)


def run_script(
        script_command, script_folder, input_folder, output_folder,
        log_folder, debug_folder):
    script_arguments = shlex.split(script_command)
    stdout_file = open(join(debug_folder, 'stdout.log'), 'w+t')
    stderr_file = open(join(debug_folder, 'stderr.log'), 'w+t')
    subprocess_options = {
        'cwd': script_folder,
        'stdout': stdout_file,
        'stderr': stderr_file,
        'encoding': 'utf-8',
        'check': True,
    }
    try:
        # TODO: Get environment variables
        subprocess.run(script_arguments, env=dict(environ, **{
            'PATH': environ.get('PATH', ''),
            'VIRTUAL_ENV': environ.get('VIRTUAL_ENV', ''),
            'CROSSCOMPUTE_INPUT_FOLDER': input_folder,
            'CROSSCOMPUTE_OUTPUT_FOLDER': output_folder,
            'CROSSCOMPUTE_LOG_FOLDER': log_folder,
            'CROSSCOMPUTE_DEBUG_FOLDER': debug_folder,
        }), **subprocess_options)
    except FileNotFoundError as e:
        raise CrossComputeDefinitionError(e)
    except CalledProcessError:
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
    test_count = len(test_dictionaries)
    d = {
        'tests total count': test_count,
        'tests passed count': test_count - len(error_by_folder),
    }
    if error_by_folder:
        d['error by folder'] = error_by_folder
        raise CrossComputeExecutionError(d)
    return d


def render_result(tool_definition, result_dictionary):
    blocks = render_blocks(tool_definition, result_dictionary)
    styles = result_dictionary.get('style', {}).get('rules', [])
    document_dictionary = {
        'blocks': blocks,
        'styles': styles,
    }
    if 'name' in result_dictionary:
        document_dictionary['name'] = result_dictionary['name']
    return document_dictionary


def render_blocks(tool_definition, result_dictionary):
    input_variable_definition_by_id = get_by_id(tool_definition[
        'input']['variables'])
    output_variable_definition_by_id = get_by_id(tool_definition[
        'output']['variables'])
    input_variable_data_by_id = get_data_by_id(result_dictionary[
        'input']['variables'])
    output_variable_data_by_id = get_data_by_id(result_dictionary[
        'output']['variables'])
    template_dictionary = get_template_dictionary(
        tool_definition, result_dictionary)
    blocks = deepcopy(template_dictionary['blocks'])
    for block in blocks:
        if 'id' not in block:
            continue
        variable_id = block['id']
        if variable_id in output_variable_definition_by_id:
            variable_definition = output_variable_definition_by_id[variable_id]
            variable_data = output_variable_data_by_id.get(variable_id, {})
        elif variable_id in input_variable_definition_by_id:
            variable_definition = input_variable_definition_by_id[variable_id]
            variable_data = input_variable_data_by_id.get(variable_id, {})
        else:
            continue
        block['name'] = variable_definition['name']
        block['view'] = variable_definition['view']
        block['data'] = variable_data
    return blocks


def load_relevant_path(path, name, kinds):
    try:
        relevant_path = find_relevant_path(path, name)
    except OSError:
        raise CrossComputeExecutionError({name: 'could not be found'})
    return load_definition(relevant_path, kinds)


def find_relevant_path(path, name):
    if not path:
        path = '.'
    if not exists(path):
        raise OSError({'path': 'is bad'})
    path = abspath(path)

    if isdir(path):
        folder = path
    else:
        base, extension = splitext(path)
        expected_extension = splitext(name)[1]
        if extension == expected_extension:
            return path
        modified_path = base + expected_extension
        if exists(modified_path):
            return modified_path
        folder = dirname(path)

    this_folder = folder
    while True:
        this_path = join(this_folder, name)
        if exists(this_path):
            break
        parent_folder = dirname(this_folder)
        if parent_folder == this_folder:
            raise OSError({'path': 'is missing'})
        this_folder = parent_folder
    return this_path


def yield_result_dictionary(result_definition):
    variable_ids = []
    data_lists = []
    for variable_dictionary in result_definition['input']['variables']:
        variable_data = variable_dictionary['data']
        if not isinstance(variable_data, list):
            continue
        variable_ids.append(variable_dictionary['id'])
        data_lists.append(variable_data)
    for variable_data_selection in product(*data_lists):
        result_dictionary = dict(result_definition)
        old_variable_id_data_generator = ((
            _['id'],
            _['data'],
        ) for _ in result_dictionary['input']['variables'])
        new_variable_id_data_generator = zip(
            variable_ids, variable_data_selection)
        variable_data_by_id = dict(chain(
            old_variable_id_data_generator,
            new_variable_id_data_generator))
        result_dictionary['input']['variables'] = [{
            'id': variable_id,
            'data': variable_data,
        } for variable_id, variable_data in variable_data_by_id.items()]
        yield result_dictionary


def get_result_folder(result_dictionary):
    folder = S['folder']
    if 'id' in result_dictionary:
        result_id = result_dictionary['id']
        result_folder = join(folder, 'results', result_id)
    else:
        drafts_folder = join(folder, 'drafts')
        result_folder = make_random_folder(drafts_folder, S['draft.id.length'])
    return result_folder


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
        if 'file' in variable_data:
            if not exists(file_path):
                # TODO: Download file to path
                pass
            continue
        if 'value' not in variable_data:
            continue
        variable_value = variable_data['value']
        variable_view = variable_definition['view']
        try:
            save_by_extension = SAVE_BY_EXTENSION_BY_VIEW[variable_view]
        except KeyError:
            raise HTTPInternalServerError({
                'view': 'is not yet implemented for save ' + variable_view})
        file_extension = splitext(file_path)[1]
        try:
            save = save_by_extension[file_extension]
        except KeyError:
            if '.*' not in save_by_extension:
                raise CrossComputeDefinitionError({
                    'path': 'has unsupported extension ' + file_extension})
            save = save_by_extension['.*']
        try:
            save(file_path, variable_value, variable_id, value_by_id_by_path)
        except ValueError:
            raise CrossComputeExecutionError({
                'path': 'is unsaveable by view ' + variable_view + file_path})
        except CrossComputeError:
            raise
        except Exception:
            print_exception(*exc_info())
            raise HTTPInternalServerError({'path': 'triggered an exception'})
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
        try:
            load_by_extension = LOAD_BY_EXTENSION_BY_VIEW[variable_view]
        except KeyError:
            raise HTTPInternalServerError({
                'view': 'is not yet implemented for load ' + variable_view})
        try:
            load = load_by_extension[file_extension]
        except KeyError:
            if '.*' not in load_by_extension:
                raise CrossComputeDefinitionError({
                    'path': 'has unsupported extension ' + file_extension})
            load = load_by_extension['.*']
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
            raise HTTPInternalServerError({'path': 'triggered an exception'})
        # TODO: Upload to google cloud if large
        variable_dictionaries.append({
            'id': variable_id, 'data': {'value': variable_value}})
    return variable_dictionaries


def process_result_input_stream(script_command, is_quiet, as_json):
    result_count = 0
    while True:
        chore_dictionary = fetch_resource('chores')
        if not chore_dictionary:
            break
        if not is_quiet:
            print('\n' + render_object(chore_dictionary, as_json))
        # TODO: Get tool script from cloud
        result_dictionary = chore_dictionary['result']
        result_token = result_dictionary['token']
        try:
            result_dictionary = run_tool(
                chore_dictionary['tool'], result_dictionary, script_command)
        except CrossComputeError as e:
            if not is_quiet:
                print(render_object(e.args[0], as_json))
            result_progress = -1
        else:
            result_progress = 100
        result_dictionary['progress'] = result_progress
        if not is_quiet:
            print(render_object(result_dictionary, as_json))
        fetch_resource(
            'results', result_dictionary['id'], method='PATCH',
            data=result_dictionary, token=result_token)
        result_count += 1
    return result_count


def get_by_id(variable_dictionaries):
    return {_['id']: _ for _ in variable_dictionaries}


def get_data_by_id(variable_dictionaries):
    return {_['id']: _['data'] for _ in variable_dictionaries}


def clean_bash_output(output_file):
    output_file.seek(0)
    # TODO: Render ansi escape codes in jupyter error dialog
    return ANSI_ESCAPE_PATTERN.sub('', output_file.read())


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
                variable_value = variable_data['value']
            except KeyError:
                continue
            if type(variable_value) not in [int, float, str]:
                continue
            variable_value_by_id[variable_id] = variable_value
    raw_result_name = result_dictionary['name']
    return raw_result_name.format_map(SafeDict(variable_value_by_id))

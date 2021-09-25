import json
from crosscompute import __version__
from crosscompute.constants import DEFAULT_VIEW_NAME
from crosscompute.exceptions import CrossComputeDefinitionError
from crosscompute.routines import (
    get_nested_value,
    get_template_dictionary,
    load_definition,
    load_raw_definition,
    normalize_automation_definition,
    normalize_data,
    normalize_data_dictionary,
    normalize_definition,
    normalize_environment_variable_dictionaries,
    normalize_file_dictionary,
    normalize_result_definition,
    normalize_test_dictionaries,
    normalize_tool_definition_head,
    normalize_tool_template_dictionaries,
    normalize_tool_variable_dictionaries,
    normalize_value,
    parse_block_dictionaries)
from http.server import BaseHTTPRequestHandler
from os import environ
from pytest import raises

from conftest import (
    flatten_values,
    start_server,
    AUTOMATION_RESULT_DEFINITION_PATH,
    EXAMPLES_FOLDER,
    PROJECT_DEFINITION_PATH,
    RESULT_BATCH_DEFINITION_PATH,
    RESULT_NESTED_DEFINITION_PATH,
    TOOL_DEFINITION_PATH,
    TOOL_MINIMAL_DEFINITION_PATH)


class NormalizeResultDefinitionRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({}).encode('utf-8'))


def test_load_project_definition():
    project_definition = load_definition(
        PROJECT_DEFINITION_PATH, kinds=['project'])
    assert_definition_types(project_definition)
    assert project_definition['kind'] == 'project'


def test_load_automation_result_definition():
    automation_definition = load_definition(
        AUTOMATION_RESULT_DEFINITION_PATH, kinds=['automation'])
    assert_definition_types(automation_definition)
    assert automation_definition['kind'] == 'result'


def test_load_result_batch_definition():
    result_definition = load_definition(
        RESULT_BATCH_DEFINITION_PATH, kinds=['result'])
    assert_definition_types(result_definition)
    assert 'name' in result_definition
    variable_dictionaries = result_definition['input']['variables']
    assert variable_dictionaries[0]['id'] == 'a'
    assert variable_dictionaries[1]['data'] == [
        {'value': 1}, {'value': 2}, {'value': 3}]
    assert len(result_definition['print']['style']['rules']) == 2


def test_load_result_nested_definition():
    result_definition = load_definition(
        RESULT_NESTED_DEFINITION_PATH, kinds=['result'])
    assert_definition_types(result_definition)
    variable_dictionaries = result_definition['input']['variables']
    assert variable_dictionaries[0]['data'][0]['value'] == 10
    assert variable_dictionaries[1]['data'][0]['value'] == 1


def test_load_tool_minimal_definition():
    tool_definition = load_definition(
        TOOL_MINIMAL_DEFINITION_PATH, kinds=['tool'])
    assert_definition_types(tool_definition)
    assert len(tool_definition['input']['variables']) == 2


def test_load_tool_definition():
    tool_definition = load_definition(
        TOOL_DEFINITION_PATH, kinds=['tool'])
    assert_definition_types(tool_definition)
    assert tool_definition['kind'] == 'tool'
    assert len(tool_definition['tests']) == 2


def test_load_raw_definition(tmpdir):
    with raises(CrossComputeDefinitionError):
        load_raw_definition(tmpdir.join('x.yml').strpath)

    source_path = tmpdir.join('x.txt').strpath
    with open(source_path, 'wt') as source_file:
        source_file.write('')
    with raises(CrossComputeDefinitionError):
        load_raw_definition(tmpdir.join('x.txt').strpath)

    source_path = tmpdir.join('x.json').strpath

    with open(source_path, 'wt') as source_file:
        json.dump({}, source_file)
    with raises(CrossComputeDefinitionError):
        load_raw_definition(source_path)

    with open(source_path, 'wt') as source_file:
        json.dump({'crosscompute': '0.0.1'}, source_file)
    with raises(CrossComputeDefinitionError):
        load_raw_definition(source_path)

    with open(source_path, 'wt') as source_file:
        json.dump({'crosscompute': __version__}, source_file)
    assert load_raw_definition(source_path) == {}


def test_normalize_definition():
    with raises(CrossComputeDefinitionError):
        normalize_definition({})
    with raises(CrossComputeDefinitionError):
        normalize_definition({'kind': 'tool'}, kinds=['result'])
    assert normalize_definition({'kind': 'x'})['kind'] == 'x'


def test_normalize_automation_definition():
    with raises(CrossComputeDefinitionError):
        normalize_automation_definition({})


def test_normalize_result_definition():
    environ['CROSSCOMPUTE_SERVER'] = start_server(
        NormalizeResultDefinitionRequestHandler)
    environ['CROSSCOMPUTE_TOKEN'] = 'x'
    result_definition = normalize_result_definition({
        'tool': {'id': 'x'}})
    assert 'tool' in result_definition


def test_normalize_tool_definition_head():
    with raises(CrossComputeDefinitionError):
        normalize_tool_definition_head({})
    d = normalize_tool_definition_head({
        'id': 'a',
        'slug': 'b',
        'name': 'c',
        'version': {'id': 'd'},
    })
    assert d['id'] == 'a'
    assert d['slug'] == 'b'
    assert d['name'] == 'c'
    assert d['version']['id'] == 'd'


def test_normalize_value():
    assert normalize_value('a', 'text') == 'a'

    with raises(CrossComputeDefinitionError):
        normalize_value('a', 'number')
    assert normalize_value('5', 'number') == 5


def test_normalize_data():
    with raises(CrossComputeDefinitionError):
        normalize_data('', 'text')
    assert normalize_data([{'value': 'a'}], 'text')[0]['value'] == 'a'
    with raises(CrossComputeDefinitionError):
        normalize_data({
            'batch': {},
        }, 'number', folder=EXAMPLES_FOLDER)
    with raises(CrossComputeDefinitionError):
        normalize_data({
            'batch': {'path': 'x.txt'},
        }, 'number', folder=EXAMPLES_FOLDER)
    assert normalize_data({
        'batch': {'path': 'result-batch.txt'},
    }, 'number', folder=EXAMPLES_FOLDER)[0]['value'] == 1
    assert normalize_data({
        'value': 1,
    }, 'number')['value'] == 1


def test_normalize_data_dictionary():
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary([], 'text')
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary({}, 'text')
    assert normalize_data_dictionary({
        'value': '1'}, 'number') == {'value': 1}
    assert normalize_data_dictionary({
        'dataset': {'id': 'x', 'version': {'id': 'a'}},
    }, 'number')['dataset']['id'] == 'x'
    assert normalize_data_dictionary({
        'file': {'id': 'x'},
    }, 'number')['file']['id'] == 'x'


def test_normalize_file_dictionary():
    with raises(CrossComputeDefinitionError):
        normalize_file_dictionary('')
    with raises(CrossComputeDefinitionError):
        normalize_file_dictionary({})
    assert normalize_file_dictionary({'id': 'a'})['id'] == 'a'


def test_normalize_tool_variable_dictionaries():
    with raises(CrossComputeDefinitionError):
        normalize_tool_variable_dictionaries([{'id': 'x'}])
    with raises(CrossComputeDefinitionError):
        normalize_tool_variable_dictionaries([{'path': 'x'}])
    d = normalize_tool_variable_dictionaries([{
        'id': 'mosquito_count', 'path': 'x'}])[0]
    assert d['name'] == 'Mosquito Count'
    assert d['view'] == DEFAULT_VIEW_NAME


def test_normalize_environment_variable_dictionaries():
    with raises(CrossComputeDefinitionError):
        normalize_environment_variable_dictionaries('')
    with raises(CrossComputeDefinitionError):
        normalize_environment_variable_dictionaries([{}])
    normalize_environment_variable_dictionaries([{'id': 'a'}])


def test_normalize_tool_template_dictionaries():
    assert len(normalize_tool_template_dictionaries([{}], [])) == 0

    d = normalize_tool_template_dictionaries([{
        'id': 'mosquito-report',
        'blocks': [{'id': 'x'}],
    }], [])[0]
    assert d['name'] == 'Mosquito Report'


def test_normalize_test_dictionaries():
    with raises(CrossComputeDefinitionError):
        normalize_test_dictionaries({})
    with raises(CrossComputeDefinitionError):
        normalize_test_dictionaries([])
    with raises(CrossComputeDefinitionError):
        normalize_test_dictionaries([[]])
    with raises(CrossComputeDefinitionError):
        normalize_test_dictionaries([{}])
    assert normalize_test_dictionaries([{'folder': 'x'}])[0]['folder'] == 'x'


def test_get_template_dictionary():
    assert get_template_dictionary('x', {'x': {}}, {})['id'] == 'generated'
    assert get_template_dictionary('x', {'x': {'templates': [{
        'id': 'standard',
    }]}}, {'template': {
        'id': 'STANDARD',
    }})['id'] == 'standard'


def test_get_nested_value():
    with raises(CrossComputeDefinitionError):
        get_nested_value({'a': []}, 'a', 'b', '')
    with raises(CrossComputeDefinitionError):
        get_nested_value({'a': {'b': []}}, 'a', 'b', {})
    with raises(CrossComputeDefinitionError):
        get_nested_value({'a': {'b': {}}}, 'a', 'b', [])
    assert get_nested_value({}, 'a', 'b', '') == ''


def test_parse_block_dictionaries():
    assert parse_block_dictionaries('', []) == []
    assert parse_block_dictionaries('{ }', [])[0]['data']['value'] == '{ }'
    assert parse_block_dictionaries('{x}', [])[0]['data']['value'] == '{x}'
    assert parse_block_dictionaries('{x}', [{'id': 'x'}])[0]['id'] == 'x'


def assert_definition_types(definition):
    for value in flatten_values(definition):
        assert type(value) in [dict, list, int, str]

import json
from crosscompute import __version__
from crosscompute.constants import DEFAULT_VIEW_NAME
from crosscompute.exceptions import CrossComputeDefinitionError
from crosscompute.routines import (
    load_definition,
    load_raw_definition,
    normalize_automation_definition,
    normalize_data_dictionary,
    normalize_definition,
    normalize_result_definition,
    normalize_test_dictionaries,
    normalize_tool_definition_head,
    normalize_tool_variable_dictionaries,
    normalize_value)
from http.server import BaseHTTPRequestHandler
from os import environ
from pytest import raises

from conftest import (
    flatten_values,
    start_server,
    AUTOMATION_RESULT_DEFINITION_PATH,
    PROJECT_DEFINITION_PATH,
    RESULT_BATCH_DEFINITION_PATH,
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
        json.dump({'crosscompute': 'x'}, source_file)
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


def test_normalize_data_dictionary():
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary([], 'text')
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary({}, 'text')
    assert normalize_data_dictionary({
        'value': '1'}, 'number') == {'value': 1}


def test_normalize_tool_variable_dictionaries():
    with raises(CrossComputeDefinitionError):
        normalize_tool_variable_dictionaries([{'id': 'x'}])
    with raises(CrossComputeDefinitionError):
        normalize_tool_variable_dictionaries([{'path': 'x'}])
    d = normalize_tool_variable_dictionaries([{
        'id': 'mosquito_count', 'path': 'x'}])[0]
    assert d['name'] == 'Mosquito Count'
    assert d['view'] == DEFAULT_VIEW_NAME


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


def assert_definition_types(definition):
    for value in flatten_values(definition):
        assert type(value) in [dict, list, int, str]

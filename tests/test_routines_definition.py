from crosscompute.exceptions import CrossComputeDefinitionError
from crosscompute.routines.definition import (
    load_definition,
    normalize_data_dictionary,
    normalize_value)
from pytest import raises

from conftest import (
    flatten_values,
    AUTOMATION_RESULT_DEFINITION_PATH,
    RESULT_BATCH_DEFINITION_PATH,
    TOOL_DEFINITION_PATH,
    TOOL_MINIMAL_DEFINITION_PATH)


def test_load_automation_result_definition():
    automation_definition = load_definition(
        AUTOMATION_RESULT_DEFINITION_PATH, kinds=['automation'])
    assert_definition_types(automation_definition)
    assert automation_definition['kind'] == 'result'


def test_load_result_batch_definition():
    result_definition = load_definition(
        RESULT_BATCH_DEFINITION_PATH, kinds=['result'])
    assert_definition_types(result_definition)
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
    assert len(tool_definition['tests']) == 2


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


def assert_definition_types(definition):
    for value in flatten_values(definition):
        assert type(value) in [dict, list, int, str]

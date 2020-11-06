from crosscompute.exceptions import CrossComputeDefinitionError
from crosscompute.routines import (
    find_relevant_path,
    load_definition,
    normalize_data_dictionary,
    normalize_value)
from os.path import basename, join, splitext
from pytest import raises

from conftest import (
    flatten_values,
    AUTOMATION_RESULT_DEFINITION_PATH,
    EXAMPLES_FOLDER,
    RESULT_BATCH_DEFINITION_PATH,
    RESULT_DEFINITION_PATH,
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
    assert variable_dictionaries[1]['data']['values'] == [1, 2, 3]
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
        'values': ['1', '2']}, 'number') == {'values': [1, 2]}
    assert normalize_data_dictionary({
        'value': '1'}, 'number') == {'value': 1}


def test_find_relevant_path():
    path = RESULT_DEFINITION_PATH
    name = basename(path)
    stem_path, good_extension = splitext(path)
    bad_extension = '.css'

    with raises(OSError):
        find_relevant_path(
            join(EXAMPLES_FOLDER, 'x' + good_extension),
            'x' + good_extension)

    assert find_relevant_path(
        path,
        'x' + good_extension,
    ) == path

    assert find_relevant_path(
        stem_path + bad_extension,
        'x' + good_extension,
    ) == path

    assert find_relevant_path(
        EXAMPLES_FOLDER,
        name,
    ) == path

    assert find_relevant_path(
        join(EXAMPLES_FOLDER, 'templates', 'output', 'standard.md'),
        name,
    ) == path

    with raises(OSError):
        find_relevant_path('/', name)


def assert_definition_types(definition):
    for value in flatten_values(definition):
        assert type(value) in [dict, list, int, str]

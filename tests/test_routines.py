from crosscompute.routines import find_relevant_path, load_tool_definition
from os.path import basename, join, splitext
from pytest import raises

from conftest import (
    flatten_values,
    EXAMPLES_FOLDER,
    RESULT_DEFINITION_PATH,
    TOOL_MINIMAL_DEFINITION_PATH)


def test_load_tool_definition():
    tool_definition = load_tool_definition(TOOL_MINIMAL_DEFINITION_PATH)
    for value in flatten_values(tool_definition):
        assert type(value) in [dict, list, int, str]
    assert len(tool_definition['input']['variables']) == 2


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

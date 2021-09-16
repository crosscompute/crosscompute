from crosscompute.routines.definition import (
    load_definition)
from crosscompute.routines.execution import (
    find_relevant_path,
    get_result_name,
    run_automation,
    yield_result_dictionary)
from os.path import basename, join, splitext
from pytest import raises

from conftest import (
    AUTOMATION_RESULT_DEFINITION_PATH,
    EXAMPLES_FOLDER,
    RESULT_BATCH_DEFINITION_PATH,
    RESULT_DEFINITION_PATH)


def test_run_automation():
    automation_definition = load_definition(
        AUTOMATION_RESULT_DEFINITION_PATH,
        ['automation'])
    d = run_automation(automation_definition, is_mock=True)
    document_dictionaries = d['documents']
    assert len(document_dictionaries) == 3
    assert document_dictionaries[0]['blocks'][-1]['data']['value'] == 2
    assert document_dictionaries[1]['blocks'][-1]['data']['value'] == 3
    assert document_dictionaries[2]['blocks'][-1]['data']['value'] == 4


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


def test_yield_result_dictionary():
    result_definition = load_definition(
        RESULT_BATCH_DEFINITION_PATH, kinds=['result'])
    result_dictionaries = list(yield_result_dictionary(result_definition))
    assert len(result_dictionaries) == 3


def test_get_result_name():
    name_template = '{a} {b}'
    assert get_result_name({'name': name_template}) == 'a b'
    assert get_result_name({
        'name': name_template,
        'input': {
            'variables': [
                {'id': 'a', 'view': 'number', 'data': {'value': 1}},
            ],
        },
    }) == '1 b'

import json

from crosscompute.exceptions import CrossComputeDataError
from crosscompute.routines import variable
from crosscompute.routines.variable import (
    apply_functions,
    load_dictionary_data,
    load_file_data,
    load_text_data,
    update_variable_data)
from pytest import raises

from invisibleroads_macros_text import format_slug


def test_apply_functions():
    with raises(KeyError):
        apply_functions('One Two', ['slug'], {})

    assert apply_functions('One Two', ['slug', ''], {
        'slug': format_slug}) == 'one-two'


def test_update_variable_data(tmp_path):
    path = tmp_path / 'variables.dictionary'

    update_variable_data(path, {'a': 1})
    with path.open('r') as f:
        d = json.load(f)
    assert d['a'] == 1

    update_variable_data(path, {'b': 2})
    with path.open('r') as f:
        d = json.load(f)
    assert d['a'] == 1
    assert d['b'] == 2

    with path.open('w') as f:
        f.write('')
    with raises(CrossComputeDataError):
        update_variable_data(path, {'c': 3})


def test_load_file_data(tmp_path):
    path = tmp_path / 'x.dictionary'

    with raises(CrossComputeDataError):
        load_file_data(path)

    json.dump({'a': 1}, path.open('wt'))
    assert load_file_data(path)['value']['a'] == 1

    path = tmp_path / 'x.txt'
    path.write_text('whee')
    assert load_file_data(path)['value'] == 'whee'

    path = tmp_path / 'x.md'
    path.write_text('whee')
    assert load_file_data(path)['path'] == path


def test_load_dictionary_data(tmp_path):
    path = tmp_path / 'x.dictionary'

    with raises(CrossComputeDataError):
        load_dictionary_data(path)

    json.dump([], path.open('wt'))
    with raises(CrossComputeDataError):
        load_dictionary_data(path)

    json.dump({'a': 1}, path.open('wt'))
    assert load_dictionary_data(path)['value']['a'] == 1


def test_load_text_data(monkeypatch, tmp_path):
    path = tmp_path / 'x.txt'

    with raises(CrossComputeDataError):
        load_text_data(path)

    path.write_text('whee')

    monkeypatch.setattr(variable, 'CACHED_FILE_SIZE_LIMIT_IN_BYTES', 0)
    assert load_text_data(path)['path'] == path

    monkeypatch.setattr(variable, 'CACHED_FILE_SIZE_LIMIT_IN_BYTES', 10)
    assert load_text_data(path)['value'] == 'whee'

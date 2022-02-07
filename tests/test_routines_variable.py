import json
from crosscompute.exceptions import CrossComputeDataError
from crosscompute.routines.variable import (
    update_variable_data)
from pytest import raises


def test_update_variable_data(tmp_path):
    target_path = tmp_path / 'variables.dictionary'
    update_variable_data(target_path, {'a': 1})
    with target_path.open('r') as f:
        d = json.load(f)
    assert d['a'] == 1
    update_variable_data(target_path, {'b': 2})
    with target_path.open('r') as f:
        d = json.load(f)
    assert d['a'] == 1
    assert d['b'] == 2
    with target_path.open('w') as f:
        f.write('')
    with raises(CrossComputeDataError):
        update_variable_data(target_path, {'c': 3})
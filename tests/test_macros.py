from crosscompute.macros import (
    get_environment_value, sanitize_json_value)
from math import nan
from os import environ
from pytest import raises


def test_get_environment_value():
    assert 'X' not in environ
    with raises(SystemExit):
        get_environment_value('X')
    assert get_environment_value('X', 'x') == 'x'
    environ['A'] = 'a'
    assert get_environment_value('A') == 'a'


def test_sanitize_json_value():
    assert sanitize_json_value(nan) is None
    assert nan not in sanitize_json_value([[nan, 1, 'a', None]])[0]
    assert nan not in sanitize_json_value({nan: nan}).keys()
    assert nan not in sanitize_json_value({nan: nan}).values()

from crosscompute.macros import (
    get_environment_value,
    is_compatible_version,
    parse_number,
    sanitize_json_value)
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


def test_is_compatible_version():
    assert is_compatible_version('1.2.3', '1.2.3.1')
    assert not is_compatible_version('1.2.3', '1.2.4')
    assert not is_compatible_version('1.2.3', '1.3.3')


def test_parse_number():
    with raises(TypeError):
        parse_number(None)
    with raises(ValueError):
        parse_number('a')
    assert str(parse_number('1')) == '1'
    assert str(parse_number('1.1')) == '1.1'

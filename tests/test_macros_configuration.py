from crosscompute.macros.configuration import (
    get_environment_value)
from os import environ
from pytest import raises


def test_get_environment_value():
    key = 'EXAMPLE_KEY'
    value = 'EXAMPLE_VALUE'
    with raises(KeyError):
        get_environment_value(key)
    assert get_environment_value(key, 'X') == 'X'
    environ[key] = value
    assert get_environment_value(key) == value

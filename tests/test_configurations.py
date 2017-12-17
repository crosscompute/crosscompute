from crosscompute.configurations import (
    find_tool_definition, find_tool_definition_by_name, get_default_key,
    get_default_value, ToolConfigurationNotFound, ToolNotSpecified,
    ToolNotFound)
from mock import MagicMock
from os.path import join
from pytest import raises

from conftest import PACKAGE_FOLDER


DEFAULT_TOOL_NAME = 'split-cashews'
TOOL_NAME = 'add-integers'
TOOL_FOLDER = join(PACKAGE_FOLDER, 'configurations')


class TestFindToolDefinition(object):

    def test_fail_without_tool_configuration(self):
        with raises(ToolConfigurationNotFound):
            find_tool_definition(join(PACKAGE_FOLDER, 'tools', 'assets'))

    def test_fail_without_tool_specificiation(self):
        with raises(ToolNotSpecified):
            find_tool_definition(TOOL_FOLDER)

    def test_fail_without_tool_identification(self):
        with raises(ToolNotFound):
            find_tool_definition(TOOL_FOLDER, DEFAULT_TOOL_NAME)

    def test_use_default_tool_name(self):
        find_tool_definition(TOOL_FOLDER, TOOL_NAME)


class TestFindToolDefinitionByName(object):

    def test_use_default_tool_name(self):
        tool_definition_by_name = find_tool_definition_by_name(
            join(TOOL_FOLDER, 'python'), DEFAULT_TOOL_NAME)
        assert TOOL_NAME in tool_definition_by_name
        assert DEFAULT_TOOL_NAME in tool_definition_by_name
        assert len(tool_definition_by_name) == 2

    def test_differentiate_tool_names(self):
        tool_definition_by_name = find_tool_definition_by_name(TOOL_FOLDER)
        assert TOOL_NAME in tool_definition_by_name
        assert TOOL_NAME + '-2' in tool_definition_by_name
        assert 'python' in tool_definition_by_name
        assert 'scala' in tool_definition_by_name
        assert len(tool_definition_by_name) == 4


def test_get_default_key():
    assert not get_default_key('a', {})
    assert get_default_key('a', {'a': 1})
    assert get_default_key('a', {'a_path': 1})
    assert get_default_key('a', {'x.a': 1})
    assert get_default_key('a', {'x.a_path': 1})

    assert not get_default_key('a_path', {'a': 1})
    assert get_default_key('a_path', {'a_path': 1})


def test_get_default_value(tool_definition, mocker):
    data_type = MagicMock()
    data_type.parse_safely.return_value = 'parsed'
    data_type.load.return_value = 'loaded'
    f = mocker.patch('crosscompute.configurations.get_data_type')
    f.return_value = data_type

    assert get_default_value('a', {}) is None
    assert get_default_value('a', {'a': 1}) == 'parsed'
    assert get_default_value('a', {'a_path': 1}) == 'loaded'
    assert get_default_value('a', {'x.a': 1}) == 'parsed'
    assert get_default_value('a', {'x.a_path': 1}) == 'loaded'

    assert get_default_value('a_path', {'a': 1}) is None
    assert get_default_value('a_path', {'a_path': 1}) == 'parsed'

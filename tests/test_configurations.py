from crosscompute.configurations import (
    find_tool_definition, find_tool_definition_by_name, get_default_key,
    get_default_value, load_tool_definition, ToolConfigurationNotFound,
    ToolNotSpecified, ToolNotFound)
from crosscompute.models import Result
from mock import MagicMock
from os.path import join
from pytest import raises

from conftest import FOLDER


CONFIGURATIONS_FOLDER = join(FOLDER, 'configurations')
FAKE_TOOL_NAME = 'split-peas'
REAL_TOOL_NAME = 'add-integers'


class TestFindToolDefinition(object):

    def test_fail_without_tool_configuration(self):
        with raises(ToolConfigurationNotFound):
            find_tool_definition(join(FOLDER, 'assets'))

    def test_fail_without_tool_specificiation(self):
        with raises(ToolNotSpecified):
            find_tool_definition(CONFIGURATIONS_FOLDER)

    def test_fail_without_tool_identification(self):
        with raises(ToolNotFound):
            find_tool_definition(CONFIGURATIONS_FOLDER, FAKE_TOOL_NAME)

    def test_use_real_tool_name(self):
        find_tool_definition(CONFIGURATIONS_FOLDER, REAL_TOOL_NAME)


class TestFindToolDefinitionByName(object):

    def test_use_default_tool_name(self):
        tool_definition_by_name = find_tool_definition_by_name(
            join(CONFIGURATIONS_FOLDER, 'aaa'), FAKE_TOOL_NAME)
        assert FAKE_TOOL_NAME in tool_definition_by_name
        assert REAL_TOOL_NAME in tool_definition_by_name
        assert len(tool_definition_by_name) == 2

    def test_differentiate_tool_names(self):
        tool_definition_by_name = find_tool_definition_by_name(
            CONFIGURATIONS_FOLDER)
        assert REAL_TOOL_NAME in tool_definition_by_name
        assert REAL_TOOL_NAME + '-2' in tool_definition_by_name
        assert 'aaa' in tool_definition_by_name
        assert 'bbb' in tool_definition_by_name
        assert len(tool_definition_by_name) == 4

    def test_skip_links(self, data_folder):
        result_folder = Result(id='bad-link').get_folder(data_folder)
        tool_definition_by_name = find_tool_definition_by_name(result_folder)
        assert len(tool_definition_by_name) == 0


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


def test_load_tool_definition(data_folder):
    with raises(ToolConfigurationNotFound):
        load_tool_definition(join(FOLDER, 'results', 'bad-link', 'f.cfg'))
    load_tool_definition(join(FOLDER, 'results', 'good-link', 'f.cfg'))

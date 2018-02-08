from crosscompute.configurations import (
    find_tool_definition, find_tool_definition_by_name, get_default_key,
    get_default_value, load_tool_definition, _parse_tool_name,
    _parse_tool_definition, _parse_tool_arguments)
from crosscompute.exceptions import (
    ToolConfigurationNotFound, ToolConfigurationNotValid, ToolNotFound,
    ToolNotSpecified)
from crosscompute.models import Result
from functools import partial
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

    def test_fail_without_tool_specification(self):
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


def test_parse_tool_name():
    f = _parse_tool_name
    with raises(ToolConfigurationNotValid):
        f('x')
    assert f('crosscompute') == ''
    assert f('crosscompute', 'x') == 'x'
    assert f('crosscompute x') == 'x'
    assert f('crosscompute x y') == 'x-y'


def test_parse_tool_definition():
    f = partial(
        _parse_tool_definition, configuration_folder='.', tool_name='x')
    with raises(ToolConfigurationNotValid):
        f({})
    with raises(ToolConfigurationNotValid):
        f({'command_template': ''})
    with raises(ToolConfigurationNotValid):
        f({'command_template': 'python run.py {x}', 'x': ''})
    with raises(ToolConfigurationNotValid):
        f({'command_template': 'python run.py {x}', 'x_path': ''})
    assert f({
        'command_template': 'python run.py {x}',
        'x': '1',
    })['show_raw_output'] is False


def test_parse_tool_arguments():
    f = _parse_tool_arguments

    d = f({'command_template': 'python run.py { a }'})
    assert d['command_template'] == '"python"\n"run.py"\n{a}'
    assert d['argument_names'] == ['a']

    d = f({'command_template': 'python run.py\n    { a }'})
    assert d['command_template'] == '"python"\n"run.py"\n{a}'
    assert d['argument_names'] == ['a']

    d = f({'command_template': 'python run.py { a = 1 }'})
    assert d['command_template'] == '"python"\n"run.py"\n{a}'
    assert d['argument_names'] == ['a']
    assert d['x.a'] == '1'

    d = f({'command_template': 'python run.py { --a=1 }'})
    assert d['command_template'] == '"python"\n"run.py"\n--a {a}'
    assert d['argument_names'] == ['a']
    assert d['x.a'] == '1'

    d = f({'command_template': 'python run.py { --a=1 }', 'x.a': '2'})
    assert d['command_template'] == '"python"\n"run.py"\n--a {a}'
    assert d['argument_names'] == ['a']
    assert d['x.a'] == '2'

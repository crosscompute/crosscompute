from crosscompute.models import Result
from crosscompute.types import DataItem
from crosscompute.scripts.serve import (
    get_result_file_response, get_tool_file_response,
    parse_result_relative_path, parse_template_parts)
from invisibleroads_macros.disk import copy_path, make_folder
from invisibleroads_macros.exceptions import BadPath
from invisibleroads_uploads.models import Upload
from invisibleroads_uploads.tests import prepare_field_storage
from os.path import join
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound
from pytest import raises
from webob.multidict import MultiDict

from conftest import TOOL_FOLDER, WheeType


class TestParseTemplate(object):

    def test_accept_whitespace(self):
        data_item = DataItem('x', '')
        data_items = [data_item]
        assert data_items == parse_template_parts('{x}', data_items)
        assert data_items == parse_template_parts('{x }', data_items)
        assert data_items == parse_template_parts('{ x}', data_items)
        assert data_items == parse_template_parts('{ x }', data_items)

    def test_recognize_names(self):
        data_item = DataItem('x', '')
        parse_template_parts('{ x : a }', [data_item])
        assert data_item.name == 'a'


class TestResultRequest(object):

    def test_ignore_explicit_path(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x_path': 'cc.ini'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'required'

    def test_reject_mismatched_data_type(
            self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_whee',)
        # Run with incompatible value
        raw_arguments = MultiDict({'x_whee': 'x'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x_whee'] == 'whee expected'
        # Run with compatible value
        raw_arguments = MultiDict({'x_whee': 'whee'})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert result.arguments == {'x_whee': 'whee'}

    def test_accept_direct_content(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x_txt': 'whee'})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'whee'

    def test_accept_empty_content(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x': ''})
        # Run without default_path
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'required'
        # Run with default_path
        default_path = join(tool_definition['configuration_folder'], 'cc.ini')
        tool_definition['x_path'] = default_path
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == open(
            default_path).read()

    def test_accept_multipart_content(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x': prepare_field_storage('x.txt', 'xyz')})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'xyz'

    def test_accept_relative_path(
            self, result_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Prepare result_folder
        result = Result(id='xyz')
        result_folder = result.get_folder(data_folder)
        bad_folder = make_folder(join(result_folder, 'bad_folder_name'))
        open(join(bad_folder, 'x.txt'), 'wt')
        x_folder = make_folder(join(result_folder, 'x'))
        open(join(x_folder, 'x.txt'), 'wt').write('whee')
        # Use bad result_id
        raw_arguments = MultiDict({'x': 'bad/x/x.txt'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad folder_name
        raw_arguments = MultiDict({'x': 'xyz/bad/x.txt'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        raw_arguments = MultiDict({'x': 'xyz/x/bad'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        raw_arguments = MultiDict({'x': 'xyz/x/../bad/run.py'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use good path
        raw_arguments = MultiDict({'x': 'xyz/x/x.txt'})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'whee'

    def test_accept_upload_id(
            self, result_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Use bad upload_id
        raw_arguments = MultiDict({'x': 'a'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that does not have expected data_type
        upload = Upload.save(data_folder, 'anonymous', 32, 'x.txt', 'x')
        raw_arguments = MultiDict({'x': upload.id})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that has expected data_type
        upload = Upload.save(data_folder, 'anonymous', 32, 'x.txt', 'whee')
        copy_path(join(upload.folder, WheeType.get_file_name()), upload.path)
        raw_arguments = MultiDict({'x': upload.id})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'whee'


def test_parse_result_relative_path():
    f = parse_result_relative_path
    for x in ('', '1', '1/x', '1/a/x'):
        with raises(ValueError):
            f(x)
    f('1/x/a')


def test_get_tool_file_response(posts_request, mocker):
    f = get_tool_file_response
    x = 'crosscompute.scripts.serve.'
    get_absolute_path = mocker.patch(x + 'get_absolute_path')
    exists = mocker.patch(x + 'exists')
    posts_request.matchdict = {'path': 'x'}
    tool_definition = {
        'configuration_folder': TOOL_FOLDER,
        'argument_names': ['a'],
        'x.a_path': 'x'}

    get_absolute_path.side_effect = BadPath()
    with raises(HTTPNotFound):
        f(posts_request, TOOL_FOLDER, tool_definition)

    get_absolute_path.side_effect = None
    exists.return_value = False
    with raises(HTTPNotFound):
        f(posts_request, TOOL_FOLDER, tool_definition)

    exists.return_value = True
    del tool_definition['x.a_path']
    with raises(HTTPNotFound):
        f(posts_request, TOOL_FOLDER, tool_definition)


def test_get_result_file_response(posts_request, result, mocker):
    x = 'crosscompute.scripts.serve.'
    get_absolute_path = mocker.patch(x + 'get_absolute_path')
    exists = mocker.patch(x + 'exists')

    posts_request.matchdict = {'folder_name': 'a', 'path': 'x'}
    with raises(HTTPForbidden):
        get_result_file_response(posts_request, result)

    posts_request.matchdict = {'folder_name': 'x', 'path': 'x'}
    get_absolute_path.side_effect = BadPath()
    with raises(HTTPNotFound):
        get_result_file_response(posts_request, result)

    get_absolute_path.side_effect = None
    exists.return_value = False
    with raises(HTTPNotFound):
        get_result_file_response(posts_request, result)

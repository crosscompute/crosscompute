from cgi import FieldStorage
from invisibleroads_macros.disk import make_folder
from os.path import join
from pyramid.httpexceptions import HTTPBadRequest
from pytest import raises
from six import StringIO

from crosscompute.types import StringType
from crosscompute.scripts.serve import parse_result_relative_path


class TestResultRequest(object):

    def test_ignore_explicit_path(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = {'x_path': 'cc.ini'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'required'

    def test_ignore_reserved_argument_name(
            self, result_request, tool_definition):
        tool_definition['argument_names'] = ('target_folder',)
        raw_arguments = {'target_folder': '/tmp'}
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert arguments == {}

    def test_reject_mismatched_data_type(
            self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_integer',)
        raw_arguments = {'x_integer': 'abc'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x_integer'] == 'expected integer'

    def test_accept_direct_content(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = {'x_txt': 'whee'}
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert open(arguments['x_path']).read() == 'whee'

    def test_accept_empty_content(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = {'x': ''}
        # Run without default_path
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'required'
        # Run with default_path
        tool_definition['x_path'] = 'cc.ini'
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert open(arguments['x_path']).read() == open(join(tool_definition[
            'configuration_folder'], 'cc.ini')).read()

    def test_accept_multipart_content(self, result_request, tool_definition):
        field_storage = FieldStorage()
        field_storage.filename = 'x.txt'
        field_storage.file = StringIO('whee')
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = {'x': field_storage}
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert open(arguments['x_path']).read() == 'whee'

    def test_accept_relative_path(
            self, result_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Prepare result_folder
        result_folder = join(data_folder, 'results', '0')
        bad_folder = make_folder(join(result_folder, 'bad_folder_name'))
        open(join(bad_folder, 'x.txt'), 'wt')
        x_folder = make_folder(join(result_folder, 'x'))
        open(join(x_folder, 'x.txt'), 'wt').write('whee')
        # Use bad result_id
        raw_arguments = {'x': 'bad/x/x.txt'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad folder_name
        raw_arguments = {'x': '0/bad/x.txt'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        raw_arguments = {'x': '0/x/bad'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        raw_arguments = {'x': '0/x/../bad/run.py'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use good path
        raw_arguments = {'x': '0/x/x.txt'}
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert open(arguments['x_path']).read() == 'whee'

    def test_accept_upload_id(
            self, result_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Prepare upload_folder
        upload_folder = make_folder(join(data_folder, 'uploads', '0', 'xyz'))
        open(join(upload_folder, 'raw.txt'), 'wt')
        open(join(upload_folder, 'name.txt'), 'wt')
        # Use bad upload_id
        raw_arguments = {'x': 'a'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that does not have expected data_type
        raw_arguments = {'x': 'xyz'}
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that has expected data_type
        file_name = StringType.get_file_name()
        open(join(upload_folder, file_name), 'wt').write('whee')
        arguments = result_request.prepare_arguments(
            tool_definition, raw_arguments)[-1]
        assert open(arguments['x_path']).read() == 'whee'


def test_parse_result_relative_path():
    f = parse_result_relative_path
    for x in ('', '1', '1/x', '1/a/x'):
        with raises(ValueError):
            f(x)
    f('1/x/a')

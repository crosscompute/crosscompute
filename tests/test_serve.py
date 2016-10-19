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
            result_request.prepare_arguments(raw_arguments, tool_definition)
        assert e.value.detail['x'] == 'required'

    def test_ignore_reserved_argument_name(
            self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('target_folder',)
        pyramid_request.params = {'target_folder': '/tmp'}
        r = ResultRequest(pyramid_request, tool_definition)
        assert r.result_arguments == {}

    def test_reject_mismatched_data_type(
            self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('x_integer',)
        pyramid_request.params = {'x_integer': 'abc'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x_integer'] == 'expected integer'

    def test_accept_direct_content(self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        pyramid_request.params = {'x_txt': 'whee'}
        r = ResultRequest(pyramid_request, tool_definition)
        assert open(r.result_arguments['x_path']).read() == 'whee'

    def test_accept_empty_content(self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        pyramid_request.params = {'x': ''}
        # Run without default_path
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'required'
        # Run with default_path
        tool_definition['x_path'] = 'cc.ini'
        r = ResultRequest(pyramid_request, tool_definition)
        assert open(r.result_arguments['x_path']).read() == open(join(
            tool_definition['configuration_folder'], 'cc.ini')).read()

    def test_accept_multipart_content(self, pyramid_request, tool_definition):
        field_storage = FieldStorage()
        field_storage.filename = 'x.txt'
        field_storage.file = StringIO('whee')
        tool_definition['argument_names'] = ('x_path',)
        pyramid_request.params = {'x': field_storage}
        r = ResultRequest(pyramid_request, tool_definition)
        assert open(r.result_arguments['x_path']).read() == 'whee'

    def test_accept_relative_path(
            self, pyramid_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Prepare result_folder
        result_folder = join(data_folder, 'results', '0')
        bad_folder = make_folder(join(result_folder, 'bad_folder_name'))
        open(join(bad_folder, 'x.txt'), 'wt')
        x_folder = make_folder(join(result_folder, 'x'))
        open(join(x_folder, 'x.txt'), 'wt').write('whee')
        # Use bad result_id
        pyramid_request.params = {'x': 'bad/x/x.txt'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use bad folder_name
        pyramid_request.params = {'x': '0/bad/x.txt'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        pyramid_request.params = {'x': '0/x/bad'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use bad path
        pyramid_request.params = {'x': '0/x/../bad/run.py'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use good path
        pyramid_request.params = {'x': '0/x/x.txt'}
        r = ResultRequest(pyramid_request, tool_definition)
        assert open(r.result_arguments['x_path']).read() == 'whee'

    def test_accept_upload_id(
            self, pyramid_request, tool_definition, data_folder):
        tool_definition['argument_names'] = ('x_path',)
        # Prepare upload_folder
        upload_folder = make_folder(join(data_folder, 'uploads', '0', 'xyz'))
        open(join(upload_folder, 'raw.txt'), 'wt')
        open(join(upload_folder, 'name.txt'), 'wt')
        # Use bad upload_id
        pyramid_request.params = {'x': 'a'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that does not have expected data_type
        pyramid_request.params = {'x': 'xyz'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that has expected data_type
        file_name = StringType.get_file_name()
        open(join(upload_folder, file_name), 'wt').write('whee')
        r = ResultRequest(pyramid_request, tool_definition)
        assert open(r.result_arguments['x_path']).read() == 'whee'


def test_parse_result_relative_path():
    f = parse_result_relative_path
    for x in ('', '1', '1/x', '1/a/x'):
        with raises(ValueError):
            f(x)
    f('1/x/a')

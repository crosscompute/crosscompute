from cgi import FieldStorage
from invisibleroads_macros.disk import make_folder
from invisibleroads_uploads.models import Upload
from os.path import join
from pyramid.httpexceptions import HTTPBadRequest
from pytest import raises
from six import BytesIO
from webob.multidict import MultiDict

from crosscompute.models import Result
from crosscompute.types import StringType
from crosscompute.scripts.serve import (
    parse_result_relative_path, parse_template)


class TestResultRequest(object):

    def test_ignore_explicit_path(self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x_path': 'cc.ini'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'required'

    def test_ignore_reserved_argument_name(
            self, result_request, tool_definition):
        tool_definition['argument_names'] = ('target_folder',)
        raw_arguments = MultiDict({'target_folder': '/tmp'})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert result.arguments == {}

    def test_reject_mismatched_data_type(
            self, result_request, tool_definition):
        tool_definition['argument_names'] = ('x_whee',)
        # Run with incompatible value
        raw_arguments = MultiDict({'x_whee': 'x'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x_whee'] == 'expected whee'
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
        field_storage = FieldStorage()
        field_storage.filename = 'x.txt'
        field_storage.file = BytesIO(b'whee')
        tool_definition['argument_names'] = ('x_path',)
        raw_arguments = MultiDict({'x': field_storage})
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'whee'

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
        # Prepare upload_folder
        upload = Upload(id='xyz', owner_id=0)
        upload_folder = make_folder(upload.get_folder(data_folder))
        open(join(upload_folder, 'raw.txt'), 'wt')
        open(join(upload_folder, 'name.txt'), 'wt')
        # Use bad upload_id
        raw_arguments = MultiDict({'x': 'a'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that does not have expected data_type
        raw_arguments = MultiDict({'x': 'xyz'})
        with raises(HTTPBadRequest) as e:
            result_request.prepare_arguments(tool_definition, raw_arguments)
        assert e.value.detail['x'] == 'invalid'
        # Use upload_id that has expected data_type
        file_name = StringType.get_file_name()
        open(join(upload_folder, file_name), 'wt').write('whee')
        result = result_request.prepare_arguments(
            tool_definition, raw_arguments)
        assert open(result.arguments['x_path']).read() == 'whee'


def test_parse_result_relative_path():
    f = parse_result_relative_path
    for x in ('', '1', '1/x', '1/a/x'):
        with raises(ValueError):
            f(x)
    f('1/x/a')


# def test_parse_template():
    # parse_template('')

from pyramid.httpexceptions import HTTPBadRequest
from pytest import raises

from crosscompute.scripts.serve import (
    ResultRequest, parse_result_relative_path)


class TestResultRequest(object):

    def test_ignore_explicit_path(self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('x_path',)
        pyramid_request.params = {'x_path': 'cc.ini'}
        with raises(HTTPBadRequest) as e:
            ResultRequest(pyramid_request, tool_definition)
        assert e.value.detail['x'] == 'required'

    def test_ignore_reserved_argument_name(
            self, pyramid_request, tool_definition):
        tool_definition['argument_names'] = ('target_folder',)
        pyramid_request.params = {'target_folder': '/tmp'}
        r = ResultRequest(pyramid_request, tool_definition)
        assert r.result_arguments == {}

    def test_reject_mismatched_data_type(
            self, pyramid_request, tool_definition):
        # check that we can't give values that don't match data types
        pass

    def test_accept_direct_content(self, pyramid_request, tool_definition):
        # test sending direct content
        pass

    def test_accept_empty_content(self, pyramid_request, tool_definition):
        # Test without default path
        # Test with default path
        pass

    def test_accept_multipart_content(self, pyramid_request, tool_definition):
        # Test sending multipart content
        pass

    def test_accept_relative_path(self, pyramid_request, tool_definition):
        # invalid result_id
        # invalid result_path
        # invalid path that goes outside parent
        # valid
        pass

    def test_accept_upload_id(self, pyramid_request, tool_definition):
        # invalid
        # valid
        pass


def test_parse_result_relative_path():
    f = parse_result_relative_path
    for x in ('', '1', '1/x', '1/a/x'):
        with raises(ValueError):
            f(x)
    f('1/x/a')

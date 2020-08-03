import requests
import shutil
from invisibleroads_macros.security import make_random_string
from io import BytesIO
from os.path import exists, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNoContent
from pytest import fixture, raises
from zipfile import ZipFile

from conftest import RESULT_FOLDER
from crosscompute.scripts.work import (
    receive_result_request, run_tool, send_result_response)


TARGET_FOLDER = join(RESULT_FOLDER, 'y')


class TestReceiveResultRequest(object):

    endpoint_url = 'https://crosscompute.com/results/pull'
    worker_token = 'x'

    def test_handle_bad_request(self, server_response, parent_folder):
        server_response.status_code = 400
        with raises(HTTPBadRequest):
            receive_result_request(
                self.endpoint_url, self.worker_token, parent_folder)

    def test_handle_no_content(self, server_response, parent_folder):
        server_response.status_code = 204
        with raises(HTTPNoContent):
            receive_result_request(
                self.endpoint_url, self.worker_token, parent_folder)

    def test_uncompress_result_folder(self, server_response, parent_folder):
        file_name = make_random_string(8) + '.txt'
        server_response.status_code = 200
        server_response._content = prepare_archive_content(file_name)
        result_folder = receive_result_request(
            self.endpoint_url, self.worker_token, parent_folder)
        assert exists(join(result_folder, file_name))


class TestRunTool(object):

    def test_save_result_properties(self, result_request_folder):
        assert not exists(join(result_request_folder, 'y'))
        assert not exists(join(result_request_folder, 'y.cfg'))
        run_tool(result_request_folder)
        assert exists(join(result_request_folder, 'y'))
        assert exists(join(result_request_folder, 'y.cfg'))


class TestSendResultResponse(object):

    endpoint_url = 'https://crosscompute.com/results/push'

    def test_handle_bad_request(self, server_response, result_response_folder):
        server_response.status_code = 400
        with raises(HTTPBadRequest):
            send_result_response(self.endpoint_url, result_response_folder)

    def test_upload_target_folder(self, mocker, result_response_folder):
        f = mocker.patch('requests.post')
        send_result_response(self.endpoint_url, result_response_folder)
        args, kw = f.call_args
        assert 'execution_time_in_seconds' in kw['data']['result_properties']
        archive_zip = ZipFile(kw['files']['target_folder'])
        assert 'story.txt' in archive_zip.namelist()


@fixture
def server_response(mocker):
    response = requests.Response()
    mocker.patch('requests.get').return_value = response
    mocker.patch('requests.post').return_value = response
    return response


@fixture
def parent_folder(tmpdir):
    return str(tmpdir)


@fixture
def result_request_folder(parent_folder):
    result_folder = join(parent_folder, 'result_request')
    shutil.copytree(
        RESULT_FOLDER, result_folder,
        ignore=lambda folder, files: ['y', 'y.cfg'])
    return result_folder


@fixture
def result_response_folder(parent_folder):
    result_folder = join(parent_folder, 'result_response')
    shutil.copytree(RESULT_FOLDER, result_folder)
    return result_folder


def prepare_archive_content(file_name, file_content=''):
    archive_file = BytesIO()
    with ZipFile(archive_file, 'w') as archive_zip:
        archive_zip.writestr(file_name, file_content)
    archive_file.seek(0)
    return archive_file.read()

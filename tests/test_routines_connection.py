from crosscompute.constants import CLIENT_URL, SERVER_URL
from crosscompute.exceptions import (
    CrossComputeConnectionError,
    CrossComputeExecutionError,
    CrossComputeImplementationError)
from crosscompute.routines import (
    fetch_resource,
    get_bash_configuration_text,
    get_echoes_client,
    get_resource_url)
from http.server import BaseHTTPRequestHandler
from pytest import raises

from conftest import start_server


class FetchResourceRequestHandler(BaseHTTPRequestHandler):
    # https://gist.github.com/nitaku/10d0662536f37a087e1b

    def do_GET(self):
        if self.path == '/files.json':
            self.send_response(500)
        elif self.path == '/datasets.json':
            self.send_response(403)
        elif self.path == '/prints.json':
            self.send_response(400)
        else:
            self.send_response(200)
        self.end_headers()
        try:
            length = int(self.headers['Content-Length'])
        except TypeError:
            pass
        else:
            self.wfile.write(self.rfile.read(length))


def test_get_bash_configuration_text():
    bash_configuration_text = get_bash_configuration_text()
    assert CLIENT_URL in bash_configuration_text
    assert SERVER_URL in bash_configuration_text
    assert 'YOUR-TOKEN' in bash_configuration_text


def test_fetch_resource():
    server_url = 'http://localhost:9999'
    with raises(CrossComputeConnectionError):
        fetch_resource('tools', server_url=server_url, token='a')

    server_url = start_server(FetchResourceRequestHandler)
    with raises(CrossComputeImplementationError):
        fetch_resource('files', data={}, server_url=server_url, token='a')
    with raises(CrossComputeConnectionError):
        fetch_resource('datasets', server_url=server_url, token='a')
    with raises(CrossComputeExecutionError):
        fetch_resource('prints', data={}, server_url=server_url, token='a')
    with raises(CrossComputeConnectionError):
        fetch_resource('tools', 'x', server_url=server_url, token='a')
    assert fetch_resource(
        'tools', 'x', data={}, server_url=server_url, token='a',
    ) == {}


def test_get_resource_url():
    server_url = 'http://example.com'
    resource_name = 'tools'
    resource_id = 'x'
    assert get_resource_url(
        server_url, resource_name,
    ) == f'{server_url}/{resource_name}.json'
    assert get_resource_url(
        server_url, resource_name, resource_id,
    ) == f'{server_url}/{resource_name}/{resource_id}.json'


def test_get_echoes_client(mocker):
    mocker.patch(
        'crosscompute.routines.connection.get_token',
        return_value='x')
    MockSSEClient = mocker.patch(
        'crosscompute.routines.connection.SSEClient')
    get_echoes_client()
    MockSSEClient.assert_called_with(f'{SERVER_URL}/echoes/x.json')

    MockSSEClient = mocker.patch(
        'crosscompute.routines.connection.SSEClient',
        side_effect=Exception())
    with raises(CrossComputeConnectionError):
        get_echoes_client()

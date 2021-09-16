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
from os import environ
from pytest import raises

from conftest import start_server


class FetchResourceRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/a.json':
            self.send_response(500)
        elif self.path == '/b.json':
            self.send_response(401)
        elif self.path == '/c.json':
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
    environ['CROSSCOMPUTE_CLIENT'] = CLIENT_URL
    environ['CROSSCOMPUTE_SERVER'] = SERVER_URL
    try:
        del environ['CROSSCOMPUTE_TOKEN']
    except KeyError:
        pass
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
        fetch_resource('a', data={}, server_url=server_url, token='a')
    with raises(CrossComputeConnectionError):
        fetch_resource('b', server_url=server_url, token='a')
    with raises(CrossComputeExecutionError):
        fetch_resource('c', data={'x': 'X'}, server_url=server_url, token='a')
    with raises(CrossComputeConnectionError):
        fetch_resource('d', 'x', server_url=server_url, token='a')
    assert fetch_resource(
        'd', 'x', data={}, server_url=server_url, token='a',
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
    environ['CROSSCOMPUTE_SERVER'] = SERVER_URL
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

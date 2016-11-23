import requests
import simplejson as json
from invisibleroads.scripts import Script
from invisibleroads_macros.configuration import load_settings
from invisibleroads_macros.disk import (
    compress_zip, make_unique_path, uncompress, HOME_FOLDER)
from invisibleroads_macros.log import print_error
from os.path import join
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPNoContent, HTTPUnauthorized)
from requests.exceptions import ConnectionError as ServerConnectionError
from six.moves.urllib.parse import urlparse as parse_url
from socketIO_client import SocketIO, SocketIONamespace
from socketIO_client.exceptions import ConnectionError as RelayConnectionError
from threading import Lock

from ..configurations import load_result_arguments, load_tool_definition
from ..scripts import run_script


class WorkScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('queue_token')
        argument_subparser.add_argument(
            '--relay_url', metavar='URL', default=RELAY_URL)
        argument_subparser.add_argument(
            '--server_url', metavar='URL', default=SERVER_URL)

    def run(self, args):
        print('Listening to %s' % args.relay_url)
        try:
            worker = Worker(args.server_url, args.queue_token)
            worker.work()
            Namespace.channel = 'q/' + args.queue_token
            Namespace.worker = worker
            socket = SocketIO(
                args.relay_url, Namespace=Namespace, wait_for_connection=False)
            socket.wait()
        except ServerConnectionError:
            print_error('The server is down. Try again later.')
        except RelayConnectionError:
            print_error('The relay is down. Try again later.')
        except HTTPBadRequest:
            print_error(
                'There was an error processing your request.\n'
                '- Check that the server URL is correct (--server_url).\n'
                '- Upgrade the framework (pip install -U crosscompute).')
        except HTTPUnauthorized:
            print_error(
                'The server rejected the token. '
                'Make sure your token is valid.')
        except KeyboardInterrupt:
            pass


class Worker(object):

    def __init__(self, server_url, queue_token):
        self.server_url = server_url
        self.queue_token = queue_token

        self.parent_folder = join(HOME_FOLDER, '.crosscompute', parse_url(
            server_url).hostname, 'results')
        self.pull_url = join(server_url, 'results', 'pull')
        self.push_url = join(server_url, 'results', 'push')

    def work(self):
        if WORKING_LOCK.locked():
            return
        with WORKING_LOCK:
            while True:
                try:
                    result_folder = receive_result_request(
                        self.pull_url, self.queue_token, self.parent_folder)
                except HTTPNoContent:
                    break
                print('\nresult_folder = %s\n' % result_folder)
                run_tool(result_folder)
                send_result_response(self.push_url, result_folder)


class Namespace(SocketIONamespace):

    def on_connect(self):
        self.emit('watch', self.channel)

    def on_reconnect(self):
        self.on_connect()

    def on_work(self, message):
        self.worker.work()


def receive_result_request(endpoint_url, queue_token, parent_folder):
    response = requests.get(endpoint_url, headers={
        'Authorization': 'Bearer ' + queue_token})
    if response.status_code == 200:
        pass
    elif response.status_code == 204:
        raise HTTPNoContent
    elif response.status_code == 401:
        raise HTTPUnauthorized
    else:
        raise HTTPBadRequest
    archive_path = make_unique_path(parent_folder, '.zip', length=16)
    open(archive_path, 'wb').write(response.content)
    result_folder = uncompress(archive_path)
    return result_folder


def run_tool(result_folder):
    f_configuration_path = join(result_folder, 'f.cfg')
    x_configuration_path = join(result_folder, 'x.cfg')
    target_folder = join(result_folder, 'y')
    tool_definition = load_tool_definition(f_configuration_path)
    result_arguments = load_result_arguments(x_configuration_path)
    environment = load_settings(x_configuration_path, 'result_environment')
    return run_script(
        tool_definition, result_arguments, result_folder, target_folder,
        environment)


def send_result_response(endpoint_url, result_folder):
    result_token = open(join(result_folder, 'y.token')).read()
    result_properties = load_settings(join(
        result_folder, 'y.cfg'), 'result_properties')  # Assume relative paths
    response = requests.post(endpoint_url, headers={
        'Authorization': 'Bearer ' + result_token,
    }, data={
        'result_progress': 100,
        'result_properties': json.dumps(result_properties),
    }, files={
        'target_folder': open(compress_zip(join(result_folder, 'y')), 'rb'),
    })
    if response.status_code == 400:
        raise HTTPBadRequest


RELAY_URL = 'https://crosscompute.com'
SERVER_URL = 'https://crosscompute.com'
WORKING_LOCK = Lock()

import requests
import simplejson as json
from invisibleroads.scripts import Script
from invisibleroads_macros.configuration import load_settings
from invisibleroads_macros.disk import (
    cd, compress_zip, make_unique_path, uncompress, HOME_FOLDER)
from invisibleroads_macros.log import print_error
from os.path import exists, expanduser, join
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPNoContent, HTTPUnauthorized)
from requests.exceptions import ConnectionError as ServerConnectionError
from six.moves.urllib.parse import urlparse as parse_url
from socketIO_client import SocketIO, SocketIONamespace
from socketIO_client.exceptions import ConnectionError as RelayConnectionError
from threading import Lock

from ..configurations import load_result_arguments, load_tool_definition
from ..scripts import run_script
from ..symmetries import subprocess


class WorkScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument(
            '--server_url', metavar='URL', default=SERVER_URL)
        argument_subparser.add_argument(
            '--relay_url', metavar='URL', default=RELAY_URL)
        argument_subparser.add_argument(
            '--processor_level', metavar='LEVEL', default=0)
        argument_subparser.add_argument(
            '--memory_level', metavar='LEVEL', default=0)
        argument_subparser.add_argument('worker_token')

    def run(self, args):
        print('server_url = %s' % args.server_url)
        print('relay_url = %s' % args.relay_url)
        try:
            worker = Worker(
                args.server_url, args.worker_token, args.processor_level,
                args.memory_level)
            Namespace.channels = ['t/%s/%s/%s' % (
                x, args.processor_level, args.memory_level,
            ) for x in worker.tool_ids]
            Namespace.worker = worker
            socket = SocketIO(
                args.relay_url, Namespace=Namespace, wait_for_connection=False)
            socket.wait(0.1)
            worker.work()
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

    def __init__(
            self, server_url, worker_token, processor_level, memory_level):
        self.server_url = server_url
        self.worker_token = worker_token
        self.processor_level = processor_level
        self.memory_level = memory_level

        d = requests.get(join(server_url, 'workers.json'), headers={
            'Authorization': 'Bearer ' + worker_token}).json()
        self.id = d['worker_id']
        self.tool_ids = d['tool_ids']

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
                        self.pull_url, self.worker_token, self.parent_folder,
                        self.processor_level, self.memory_level)
                except HTTPNoContent as e:
                    break
                print('\nresult_folder = %s\n' % result_folder)
                run_tool(result_folder)
                send_result_response(self.push_url, result_folder)


class Namespace(SocketIONamespace):

    def on_connect(self):
        worker_id = self.worker.id
        for channel in self.channels:
            self.emit('watch', channel, worker_id)

    def on_reconnect(self):
        self.on_connect()

    def on_work(self):
        self.worker.work()


def receive_result_request(
        endpoint_url, worker_token, parent_folder, processor_level=0,
        memory_level=0):
    d = {
        'processor_level': processor_level,
        'memory_level': memory_level,
    }
    if 'environment_id' in S:
        d['environment_id'] = S['environment_id']
    response = requests.get(endpoint_url, d, headers={
        'Authorization': 'Bearer ' + worker_token})
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
    tool_folder = tool_definition['configuration_folder']
    tool_id = load_settings(f_configuration_path, 'tool_location')['tool_id']
    result_arguments = load_result_arguments(
        x_configuration_path, tool_definition)
    environment = load_settings(x_configuration_path, 'environment_variables')

    setup_path = join(tool_folder, 'setup.sh')
    if exists(setup_path) and tool_id not in TOOL_IDS:
        process_arguments = ['bash', setup_path]
        with cd(tool_folder):
            subprocess.call(
                process_arguments,
                stdout=open(join(result_folder, 'setup.log'), 'wt'),
                stderr=subprocess.STDOUT,
                env=environment)
        TOOL_IDS.append(tool_id)

    return run_script(
        tool_definition, result_arguments, result_folder, target_folder,
        environment)


def run_setup(tool_folder, result_folder):
    pass


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
TOOL_IDS = []
WORKING_LOCK = Lock()
SETTINGS_PATH = expanduser('~/.crosscompute/.settings.ini')
S = load_settings(SETTINGS_PATH, 'crosscompute-website')

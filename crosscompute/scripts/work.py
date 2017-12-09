import requests
import simplejson as json
from invisibleroads.scripts import Script
from invisibleroads_macros.configuration import load_settings
from invisibleroads_macros.disk import (
    cd, compress_zip, load_text, make_unique_path, uncompress, HOME_FOLDER)
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
            '--processor_level', metavar='LEVEL', default=PROCESSOR_LEVEL)
        argument_subparser.add_argument(
            '--memory_level', metavar='LEVEL', default=MEMORY_LEVEL)
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
            ) for x in worker.tool_ids] + ['w/%s' % worker.id]
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

        response = requests.get(join(server_url, 'workers.json'), headers={
            'Authorization': 'Bearer ' + worker_token})
        status_code = response.status_code
        if status_code == 200:
            pass
        elif status_code == 401:
            raise HTTPUnauthorized
        else:
            raise HTTPBadRequest
        d = response.json()
        self.id = d['worker_id']
        self.tool_ids = d['tool_ids']
        print('worker_id = %s' % self.id)

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
    run_setup(tool_folder, tool_id, result_folder, environment)
    return run_script(
        tool_definition, result_arguments, result_folder, target_folder,
        environment)


def run_setup(tool_folder, tool_id, result_folder, environment):
    tool_setup_path = join(tool_folder, 'setup.sh')
    if not exists(tool_setup_path):
        return
    if tool_id in TOOL_IDS:
        return
    if 'setup_header' in S:
        setup_header = S['setup_header'].strip()
        setup_main = load_text(tool_setup_path)
        setup_content = setup_header + '\n' + setup_main
        setup_path = make_unique_path(tool_folder, '.sh', 'setup-')
        open(setup_path, 'wt').write(setup_content)
    else:
        setup_path = tool_setup_path
    process_arguments = ['bash', setup_path]
    log_path = join(result_folder, 'setup.log')
    with cd(tool_folder):
        subprocess.call(
            process_arguments,
            stdout=open(log_path, 'wt'),
            stderr=subprocess.STDOUT,
            env=environment)
    TOOL_IDS.append(tool_id)


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


TOOL_IDS = []
WORKING_LOCK = Lock()
SETTINGS_PATH = expanduser('~/.crosscompute/.settings.ini')
S = load_settings(SETTINGS_PATH, 'crosscompute-website')
SERVER_URL = S.get('server_url', 'https://crosscompute.com')
RELAY_URL = S.get('relay_url', 'https://crosscompute.com')
PROCESSOR_LEVEL = S.get('processor_level', 0)
MEMORY_LEVEL = S.get('memory_level', 0)

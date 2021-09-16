import socket
from collections.abc import ByteString, Sequence
from http.server import HTTPServer
from os.path import dirname, join
from threading import Thread


TESTS_FOLDER = dirname(__file__)
EXAMPLES_FOLDER = join(TESTS_FOLDER, 'examples')
PROJECT_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'project.yml')
AUTOMATION_RESULT_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'automation.yml')
RESULT_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'result.yml')
RESULT_BATCH_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'result-batch.yml')
RESULT_NESTED_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'result-nested.yml')
TOOL_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'tool.yml')
TOOL_MINIMAL_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'tool-minimal.yml')


def flatten_values(d):
    values = []
    vs = [d]
    for v in vs:
        if hasattr(v, 'items'):
            vs.extend(v.values())
        elif isinstance(v, Sequence) and not isinstance(v, (str, ByteString)):
            vs.extend(v)
        values.append(v)
    return values


def start_server(RequestHandler):
    ip, port = make_server_address()
    server = HTTPServer((ip, port), RequestHandler)
    server_thread = Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()
    return f'http://{ip}:{port}'


def make_server_address():
    # https://realpython.com/testing-third-party-apis-with-mock-servers
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port

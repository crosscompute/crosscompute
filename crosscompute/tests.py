import json
from bs4 import BeautifulSoup
from six.moves.urllib.parse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from .models import Result
from .types import initialize_data_types
from .scripts import prepare_tool_definition, run_script
from .scripts.serve import get_app


def run(data_folder, tool_name, result_arguments=None):
    initialize_data_types()
    tool_definition = prepare_tool_definition(tool_name)
    result = Result.spawn(data_folder)
    target_folder = result.get_target_folder(data_folder)
    return run_script(
        tool_definition, result_arguments or {}, result.folder, target_folder)


def serve(data_folder, tool_name, result_arguments=None):
    initialize_data_types()
    response, client = _prepare_response(
        data_folder, tool_name, result_arguments)
    result_url = json.loads(response.data.decode('utf-8'))['result_url']
    with client.get(parse_url(result_url).path) as response:
        soup = BeautifulSoup(response.data, 'html.parser')
    return soup, client


def serve_bad_request(data_folder, tool_name, result_arguments=None):
    response, client = _prepare_response(
        data_folder, tool_name, result_arguments)
    assert response.status_code == 400, response.data
    return json.loads(response.data.decode('utf-8'))


def _prepare_response(data_folder, tool_name, result_arguments):
    tool_definition = prepare_tool_definition(tool_name)
    app = get_app(tool_definition, data_folder)
    client = Client(app, BaseResponse)
    with client.post('/t/1.json', data=result_arguments or {}) as response:
        return response, client

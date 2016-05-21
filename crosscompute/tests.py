import json
from bs4 import BeautifulSoup
from crosscompute.types import get_data_type_by_suffix
from crosscompute.scripts import (
    load_tool_definition, prepare_result_response_folder, run_script)
from crosscompute.scripts.serve import get_app
from six.moves.urllib.parse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse


def run(data_folder, tool_name, result_arguments=None):
    target_folder = prepare_result_response_folder(data_folder)[1]
    tool_definition = load_tool_definition(tool_name)
    return run_script(
        target_folder, tool_definition, result_arguments or {},
        get_data_type_by_suffix())


def serve(data_folder, tool_name, result_arguments=None):
    response, client = _prepare_response(
        data_folder, tool_name, result_arguments)
    assert response.status_code == 303, response.data
    result_url = parse_url(dict(response.headers)['Location']).path
    with client.get(result_url) as response:
        soup = BeautifulSoup(response.data, 'html.parser')
    return soup, client


def serve_bad_request(data_folder, tool_name, result_arguments=None):
    response, client = _prepare_response(
        data_folder, tool_name, result_arguments)
    assert response.status_code == 400, response.data
    return json.loads(response.data.decode('utf-8'))


def _prepare_response(data_folder, tool_name, result_arguments):
    tool_definition = load_tool_definition(tool_name)
    app = get_app(tool_definition, data_folder, 'Test', 'Python')
    client = Client(app, BaseResponse)
    with client.post('/t/1', data=result_arguments or {}) as response:
        return response, client

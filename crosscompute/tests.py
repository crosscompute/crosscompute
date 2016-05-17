from bs4 import BeautifulSoup
from crosscompute.configurations import get_tool_definition
from crosscompute.scripts import run_script
from crosscompute.scripts.serve import get_app
from crosscompute.types import get_data_type_by_suffix
from invisibleroads_macros.disk import make_enumerated_folder, make_folder
from os.path import join
from urlparse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse


TARGET_FOLDER = '/tmp/crosscompute/tests'


def run(tool_folder, tool_name, result_arguments=None):
    target_folder = make_folder(join(make_enumerated_folder(join(
        TARGET_FOLDER, tool_name, 'results')), 'response'))
    return run_script(
        target_folder,
        get_tool_definition(tool_folder, tool_name),
        result_arguments or {},
        get_data_type_by_suffix())


def serve(tool_folder, tool_name, result_arguments=None):
    tool_definition = get_tool_definition(tool_folder, tool_name)
    app = get_app(tool_definition, data_folder=join(TARGET_FOLDER, tool_name))
    client = Client(app, BaseResponse)
    with client.post('/t/1', data=result_arguments or {}) as response:
        assert 303 == response.status_code
    result_url = parse_url(dict(response.headers)['Location']).path
    with client.get(result_url) as response:
        soup = BeautifulSoup(response.data, 'lxml')
    return soup, client

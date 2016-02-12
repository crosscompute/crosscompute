from bs4 import BeautifulSoup
from urlparse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from conftest import TOOL_FOLDER
from crosscompute.configurations import get_tool_definition
from crosscompute.scripts.serve import get_app


def test_serve():
    tool_definition = get_tool_definition(TOOL_FOLDER, 'count-characters')
    client = Client(get_app(tool_definition), BaseResponse)
    response = client.post('/tools/1', data=dict(phrase='welcome'))
    assert 303 == response.status_code
    result_url = parse_url(dict(response.headers)['Location']).path
    response = client.get(result_url)
    soup = BeautifulSoup(response.data)
    assert '7' in soup.find('div', id='standard_output_').text.strip()

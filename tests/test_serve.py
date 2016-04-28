from bs4 import BeautifulSoup
from urlparse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from conftest import TOOL_FOLDER
from crosscompute.configurations import get_tool_definition
from crosscompute.scripts.serve import get_app


# serve function passes first test to use it, then fails subsequent calls
def serve(tool_name, arguments=None):
    tool_definition = get_tool_definition(TOOL_FOLDER, tool_name)
    # get_app function returns error
    app = get_app(tool_definition)
    client = Client(app, BaseResponse)
    response = client.post('/tools/1', data=arguments)
    assert 303 == response.status_code
    response.close()
    result_url = parse_url(dict(response.headers)['Location']).path
    response = client.get(result_url)
    soup = BeautifulSoup(response.data)
    response.close()
    return soup


def test_serve():
    soup = serve('count-characters', dict(phrase='welcome'))
    assert '7' in soup.find(id='standard_output_').text.strip()

from lxml.html import fromstring
from lxml.cssselect import CSSSelector
from urlparse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from conftest import EXAMPLES_FOLDER
from crosscompute.configurations import get_tool_definition
from crosscompute.scripts.serve import get_app


def test_serve():
    tool_definition = get_tool_definition(EXAMPLES_FOLDER, 'add-integers')
    client = Client(get_app(tool_definition), BaseResponse)
    response = client.post('/tools/0', data=dict(x_integer=2, y_integer=3))
    assert 303 == response.status_code
    result_url = parse_url(dict(response.headers)['Location']).path
    response = client.get(result_url)
    element = fromstring(response.data)
    assert '5' == CSSSelector('#standard_output_')(element)[0].text.strip()

from os.path import exists
from lxml.html import fromstring
from lxml.cssselect import CSSSelector
from pytest import mark
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from conftest import ADD_INTEGERS_FOLDER, EXAMPLES_FOLDER, SUBMODULES_REQUIRED
from crosscompute.configurations import get_tool_definition
from crosscompute.scripts.serve import get_app


@mark.skipif(not exists(ADD_INTEGERS_FOLDER), reason=SUBMODULES_REQUIRED)
def test_serve():
    tool_definition = get_tool_definition(EXAMPLES_FOLDER, 'add-integers')
    client = Client(get_app(tool_definition), BaseResponse)
    response = client.post(data=dict(x_integer=2, y_integer=3))
    element = fromstring(response.data)
    assert '5' == CSSSelector('#standard_output_')(element)[0].text.strip()

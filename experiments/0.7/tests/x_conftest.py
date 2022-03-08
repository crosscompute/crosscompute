from collections import OrderedDict
from invisibleroads_macros.disk import copy_folder
from os.path import dirname, join
from pytest import fixture

from crosscompute.exceptions import DataTypeError
from crosscompute.models import Result
from crosscompute.scripts.serve import ResultRequest
from crosscompute.types import StringType, DATA_TYPE_BY_SUFFIX


@fixture
def tool_definition():
    return OrderedDict([
        ('argument_names', ()),
        ('configuration_folder', TOOL_FOLDER),
        ('a_path', 1),
        ('a', 2),
        ('x.a_path', 3),
        ('x.a', 4)
    ])


@fixture
def result(data_folder):
    result = Result(id=1)
    result_folder = result.get_folder(data_folder)
    copy_folder(result_folder, RESULT_FOLDER)
    return result


@fixture
def result_request(posts_request):
    return ResultRequest(posts_request)


FOLDER = dirname(__file__)
TOOL_FOLDER = join(FOLDER, 'tools', 'multiple-tools')
RESULT_FOLDER = join(FOLDER, 'results', 'no-links')


pytest_plugins = [
    'invisibleroads_posts.tests',
    'invisibleroads_uploads.tests',
]

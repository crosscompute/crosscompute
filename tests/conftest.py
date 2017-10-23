from collections import OrderedDict
from invisibleroads_macros.disk import get_package_folder
from os.path import join
from pytest import fixture

from crosscompute.exceptions import DataTypeError
from crosscompute.scripts.serve import ResultRequest
from crosscompute.types import StringType, DATA_TYPE_BY_SUFFIX


class WheeType(StringType):

    @classmethod
    def parse(Class, x, default_value=None):
        if x != 'whee':
            raise DataTypeError('expected whee')
        return x


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
def result_request(posts_request):
    return ResultRequest(posts_request)


DATA_TYPE_BY_SUFFIX['whee'] = WheeType
PACKAGE_FOLDER = get_package_folder(__file__)
TOOL_FOLDER = join(PACKAGE_FOLDER, 'tools')


pytest_plugins = [
    'invisibleroads_posts.tests',
    'invisibleroads_uploads.tests',
]

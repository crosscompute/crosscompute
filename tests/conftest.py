from invisibleroads_macros.disk import get_package_folder
from os.path import join
from pytest import fixture

from crosscompute.scripts.serve import ResultRequest
from crosscompute.types import DataTypeError, StringType, DATA_TYPE_BY_SUFFIX


class WheeType(StringType):

    @classmethod
    def parse(Class, text):
        if text != 'whee':
            raise DataTypeError('expected whee')
        return text


@fixture
def tool_definition():
    return {
        'argument_names': (),
        'configuration_folder': TOOL_FOLDER,
    }


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

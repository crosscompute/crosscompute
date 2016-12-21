from invisibleroads_macros.disk import get_package_folder, remove_safely
from os.path import join
from pyramid import testing
from pytest import fixture

from crosscompute.scripts.serve import ResultRequest
from crosscompute.types import DataType, DataTypeError, DATA_TYPE_BY_SUFFIX


class WheeType(DataType):

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
def result_request(pyramid_request):
    return ResultRequest(pyramid_request)


@fixture
def pyramid_request(config, data_folder):
    return testing.DummyRequest(data_folder=data_folder)


@fixture
def config(settings):
    config = testing.setUp(settings=settings)
    yield config
    testing.tearDown()


@fixture
def settings(data_folder):
    return {
        'data.folder': data_folder,
    }


@fixture
def data_folder(tmpdir):
    data_folder = str(tmpdir)
    yield data_folder
    remove_safely(data_folder)


DATA_TYPE_BY_SUFFIX['whee'] = WheeType
PACKAGE_FOLDER = get_package_folder(__file__)
TOOL_FOLDER = join(PACKAGE_FOLDER, 'tools')

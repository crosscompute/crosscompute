from invisibleroads_macros.disk import get_package_folder, remove_safely
from os.path import join
from pyramid import testing
from pytest import fixture


TOOL_FOLDER = join(get_package_folder(__file__), 'tools')


@fixture
def tool_definition():
    return {
        'argument_names': (),
        'configuration_folder': TOOL_FOLDER,
    }


@fixture
def pyramid_request(config):
    return testing.DummyRequest()


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

from abc import ABC, abstractmethod

from ..constants import (
    HOST,
    PORT)


class Automation(ABC):

    @classmethod
    def load(Class, path_or_folder):
        return Class()

    @abstractmethod
    def run(self, environment, is_in=None, with_rebuild=True):
        pass

    @abstractmethod
    def serve(
            self, environment, host=HOST, port=PORT, with_restart=True,
            with_prefix=True, with_hidden=True, root_uri='',
            allowed_origins=None):
        pass


class Batch(ABC):

    @abstractmethod
    def load_data(self, variable_definition):
        '''
        Load the data of the variable in one of the following formats:
        {}
        {'value': 1}
        {'path': '/a/b/c.png'}
        {'uri': '/f/abc'}
        {'error': 'message'}
        '''
        return {}

    @abstractmethod
    def get_data_uri(self, variable_definition):
        'Get the resolved variable data uri'
        return ''

    @abstractmethod
    def get_data_configuration(self, variable_definition):
        'Get the resolved variable configuration'
        return {}

    @abstractmethod
    def is_done(self):
        return False


class Server(ABC):

    @abstractmethod
    def serve(self, configuration):
        pass

    @abstractmethod
    def watch(self, configuration, reload):
        pass

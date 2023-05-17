from abc import ABC, abstractmethod


class Automation(ABC):

    @classmethod
    def load(Class, path_or_folder):
        return Class()

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def serve(self):
        pass


class Batch(ABC):

    @abstractmethod
    def get_data(self, variable_definition):
        '''
        Get the data of the variable in one of the following formats:
        {}
        {'value': 1}
        {'path': '/a/b/c.png'}
        {'uri': 'upload:xyz'}
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


class Server(ABC):

    @abstractmethod
    def __init__(self, configuration, work=None, queue=None, settings=None):
        pass

    @abstractmethod
    def serve(self):
        pass

    @abstractmethod
    def watch(self):
        pass

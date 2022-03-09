from abc import ABC


class Automation(ABC):

    @classmethod
    def load(Class, path_or_folder):
        return Class()

    def run(self):
        pass

    def serve(self):
        pass


class Batch(ABC):

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

    def get_data_uri(self, variable_definition):
        'Get the resolved variable data uri'
        return ''

    def get_data_configuration(self, variable_definition):
        'Get the resolved variable configuration'
        return {}


class Server(ABC):

    def __init__(self, configuration, work=None, queue=None, settings=None):
        pass

    def run(self):
        pass

    def watch(self):
        pass

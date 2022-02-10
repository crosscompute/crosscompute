from abc import ABC


class BatchInterface(ABC):

    def get_data(self, variable_definition):
        '''
        Get the data of the variable in one of the following formats:
        {'value': 1}
        {'path': '/a/b/c.png'}
        {'uri': 'upload:xyz'}
        '''
        pass

    def get_data_uri(self, variable_definition):
        'Get the resolved variable data uri'
        pass

    def get_data_configuration(self, variable_definition):
        'Get the resolved variable configuration'
        pass

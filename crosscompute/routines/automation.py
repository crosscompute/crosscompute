from logging import getLogger
from multiprocessing import Value
from os import listdir
from os.path import isdir
from time import time

from ..constants import AUTOMATION_PATH
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from .configuration import (
    get_automation_definitions,
    load_configuration)


class Automation():

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        if isdir(path_or_folder):
            instance.initialize_from_folder(path_or_folder)
        else:
            instance.initialize_from_path(path_or_folder)
        return instance

    def initialize_from_folder(self, configuration_folder):
        paths = listdir(configuration_folder)
        if AUTOMATION_PATH in paths:
            paths.remove(AUTOMATION_PATH)
            paths.insert(0, AUTOMATION_PATH)
        for path in paths:
            if isdir(path):
                continue
            try:
                self.initialize_from_path(path)
            except CrossComputeConfigurationError:
                raise
            except CrossComputeError:
                continue
            break
        else:
            raise CrossComputeError('could not find configuration')

    def initialize_from_path(self, configuration_path):
        configuration = load_configuration(configuration_path)
        automation_folder = configuration['folder']
        automation_definitions = get_automation_definitions(
            configuration)

        self.configuration_path = configuration_path
        self.configuration = configuration
        self.automation_folder = automation_folder
        self.automation_definitions = automation_definitions
        self.timestamp_object = Value('d', time())

        L.debug('configuration_path = %s', configuration_path)
        L.debug('automation_folder = %s', automation_folder)


L = getLogger(__name__)

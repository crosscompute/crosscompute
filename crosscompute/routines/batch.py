import json
from invisibleroads_macros_log import format_path
from logging import getLogger

from ..constants import (
    MODE_CODE_BY_NAME,
    MODE_ROUTE,
    VARIABLE_ROUTE)
from ..exceptions import (
    CrossComputeDataError)
from .configuration import (
    BatchDefinition,
    VariableDefinition)
from .interface import Batch
from .variable import (
    load_variable_data)


class DiskBatch(Batch):

    def __init__(self, automation_definition, batch_definition):
        batch_definition = BatchDefinition(batch_definition)
        self.automation_definition = automation_definition
        self.batch_definition = batch_definition
        self.folder = automation_definition.folder / batch_definition.folder

    def get_variable_configuration(self, variable_definition):
        variable_definition = VariableDefinition(variable_definition)
        variable_configuration = variable_definition.configuration
        configuration_path = variable_configuration.path
        if configuration_path:
            mode_name = variable_definition.mode_name
            path = self.folder / mode_name / configuration_path
            try:
                variable_configuration.update(json.load(open(path, 'rt')))
            except OSError:
                L.error('path not found %s', format_path(path))
            except json.JSONDecodeError:
                L.error('must be json %s', format_path(path))
            except TypeError:
                L.error('must contain a dictionary %s', format_path(path))
        return variable_configuration

    def get_data(self, variable_definition):
        variable_definition = VariableDefinition(variable_definition)
        variable_path = variable_definition.path
        if variable_path == 'ENVIRONMENT':
            return {}
        mode_name = variable_definition.mode_name
        variable_id = variable_definition.id
        try:
            variable_data = load_variable_data(
                self.folder / mode_name / variable_path, variable_id)
        except CrossComputeDataError as e:
            return {'error': e}
        return variable_data

    def get_data_uri(self, variable_definition):
        variable_definition = VariableDefinition(variable_definition)
        automation_uri = self.automation_definition.uri
        batch_uri = self.batch_definition.uri
        mode_code = MODE_CODE_BY_NAME[variable_definition.mode_name]
        mode_uri = MODE_ROUTE.format(mode_code=mode_code)
        variable_uri = VARIABLE_ROUTE.format(
            variable_id=variable_definition.variable_id)
        return automation_uri + batch_uri + mode_uri + variable_uri


L = getLogger(__name__)

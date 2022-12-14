import json
from invisibleroads_macros_log import format_path
from logging import getLogger

from ..constants import (
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ROUTE)
from ..exceptions import (
    CrossComputeDataError)
from .interface import Batch
from .variable import (
    load_variable_data)


class DiskBatch(Batch):

    def __init__(
            self,
            automation_definition,
            batch_definition,
            request_params=None):
        self.automation_definition = automation_definition
        self.batch_definition = batch_definition
        self.request_params = request_params or {}
        self.folder = automation_definition.folder / batch_definition.folder

    def get_variable_configuration(self, variable_definition):
        folder = self.folder
        variable_configuration = variable_definition.configuration.copy()
        if 'path' in variable_configuration:
            relative_path = variable_configuration['path']
            is_customized = True
        else:
            relative_path = str(variable_definition.path) + '.configuration'
            is_customized = False
        step_name = variable_definition.step_name
        path = folder / step_name / relative_path
        if not is_customized and not path.exists():
            return variable_configuration
        try:
            with path.open('rt') as f:
                d = json.load(f)
            variable_configuration.update(d)
        except OSError:
            L.error('path not found %s', format_path(path))
        except json.JSONDecodeError:
            L.error('must be json %s', format_path(path))
        except TypeError:
            L.error('must contain a dictionary %s', format_path(path))
        return variable_configuration

    def get_data(self, variable_definition):
        variable_data = self.get_data_from_request(variable_definition)
        if variable_data:
            return variable_data
        variable_path = variable_definition.path
        if variable_path == 'ENVIRONMENT':
            return {}
        variable_id = variable_definition.id
        step_name = variable_definition.step_name
        path = self.folder / step_name / variable_path
        try:
            variable_data = load_variable_data(path, variable_id)
        except CrossComputeDataError as e:
            L.warning(e)
            return {'error': e}
        return variable_data

    def get_data_from_request(self, variable_definition):
        variable_id = variable_definition.id
        params = self.request_params
        if variable_id in params:
            return {'value': params[variable_id]}
        return {}

    def get_data_uri(self, variable_definition, element):
        root_uri = element.root_uri
        automation_uri = self.automation_definition.uri
        batch_uri = self.batch_definition.uri
        step_code = STEP_CODE_BY_NAME[variable_definition.step_name]
        step_uri = STEP_ROUTE.format(step_code=step_code)
        variable_uri = VARIABLE_ROUTE.format(
            variable_id=variable_definition.id)
        return root_uri + automation_uri + batch_uri + step_uri + variable_uri


L = getLogger(__name__)

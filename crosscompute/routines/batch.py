import json
from invisibleroads_macros_log import format_path
from logging import getLogger

from ..constants import (
    MODE_CODE_BY_NAME,
    MODE_ROUTE,
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
        variable_configuration = variable_definition.configuration
        if 'path' in variable_configuration:
            relative_path = variable_configuration['path']
            is_customized = True
        else:
            relative_path = str(variable_definition.path) + '.configuration'
            is_customized = False
        mode_name = variable_definition.mode_name
        path = folder / mode_name / relative_path
        if not is_customized and not path.exists():
            return variable_configuration
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
        variable_id = variable_definition.id
        params = self.request_params
        if variable_id in params:
            return {'value': params[variable_id]}
        variable_path = variable_definition.path
        if variable_path == 'ENVIRONMENT':
            return {}
        mode_name = variable_definition.mode_name
        path = self.folder / mode_name / variable_path
        try:
            variable_data = load_variable_data(path, variable_id)
        except CrossComputeDataError as e:
            L.warning(e)
            return {'error': e}
        return variable_data

    def get_data_uri(self, variable_definition, element):
        root_uri = element.root_uri
        automation_uri = self.automation_definition.uri
        batch_uri = self.batch_definition.uri
        mode_code = MODE_CODE_BY_NAME[variable_definition.mode_name]
        mode_uri = MODE_ROUTE.format(mode_code=mode_code)
        variable_uri = VARIABLE_ROUTE.format(
            variable_id=variable_definition.id)
        return root_uri + automation_uri + batch_uri + mode_uri + variable_uri


L = getLogger(__name__)

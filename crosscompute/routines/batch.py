import json
from logging import getLogger

from invisibleroads_macros_log import format_path

from ..constants import (
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ROUTE)
from ..exceptions import (
    CrossComputeDataError)
from ..settings import (
    template_globals)
from .interface import Batch
from .variable import (
    get_data_from,
    load_variable_data)


class DiskBatch(Batch):

    def __init__(self, automation_definition, batch_definition):
        self.automation_definition = automation_definition
        self.batch_definition = batch_definition
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

    def load_data_from(self, request_params, variable_definition):
        return get_data_from(
            request_params, variable_definition,
        ) or self.load_data(variable_definition)

    def load_data(self, variable_definition):
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

    def get_data_uri(self, variable_definition, element):
        root_uri = template_globals['root_uri']
        automation_uri = self.automation_definition.uri
        batch_uri = self.batch_definition.uri
        step_code = STEP_CODE_BY_NAME[variable_definition.step_name]
        step_uri = STEP_ROUTE.format(step_code=step_code)
        variable_uri = VARIABLE_ROUTE.format(
            variable_id=variable_definition.id)
        return root_uri + automation_uri + batch_uri + step_uri + variable_uri

    def is_done(self):
        if self.automation_definition.interval_timedelta:
            return False
        batch_definition = self.batch_definition
        if hasattr(batch_definition, 'is_done'):
            return True
        path = self.folder / 'debug' / 'variables.dictionary'
        try:
            with path.open('rt') as f:
                d = json.load(f)
            is_done = 'return_code' in d
        except (OSError, ValueError):
            return False
        if is_done:
            batch_definition.is_done = True
        return is_done


L = getLogger(__name__)

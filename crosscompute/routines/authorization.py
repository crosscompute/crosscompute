import json
from logging import getLogger
from types import FunctionType

from ..macros.iterable import find_item
from ..routines.batch import DiskBatch
from ..settings import site


class AuthorizationGuard():

    def __init__(self, identities):
        self.identities = identities

    def check(self, permission_id, configuration):
        group_definitions = configuration.group_definitions
        if not group_definitions:
            return True
        identities = self.identities
        try:
            group_definition = find_group_definition(
                group_definitions, identities)
        except StopIteration:
            return False
        for permission_definition in group_definition.permissions:
            if permission_definition.id != permission_id:
                continue
            action = permission_definition.action
            if action == 'match':
                return define_is_match(identities)
            else:
                return True
        return False

    def put(self, identities, time_in_seconds):
        return site['safe'].put(identities, time_in_seconds)

    def get_automation_definitions(self, configuration):
        return [
            _ for _ in configuration.automation_definitions
            if self.check('see_automation', _)]

    def get_batch_definitions(self, configuration):
        is_match = self.check('see_batch', configuration)
        if not is_match:
            return []
        batch_definitions = configuration.batch_definitions
        if site['with_hidden']:
            batch_definitions = [_ for _ in batch_definitions if not _.is_run]
        if not isinstance(is_match, FunctionType):
            return batch_definitions
        return [
            _ for _ in batch_definitions
            if is_match(DiskBatch(configuration, _))]

    def save_identities(self, target_path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open('wt') as f:
            json.dump(self.identities, f)


def define_is_match(identities):

    def is_match(batch):
        automation_definition = batch.automation_definition
        variable_definitions = automation_definition.get_variable_definitions(
            'input')
        for name, value in identities.items():
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', name)
            except StopIteration:
                continue
            data = batch.load_data(variable_definition)
            if not has_match(value, data.get('value')):
                return False
        return True

    return is_match


def find_group_definition(group_definitions, value_by_name):
    for group_definition in group_definitions:
        is_match = True
        for name, value in group_definition.configuration.items():
            try:
                v = value_by_name[name]
            except KeyError:
                is_match = False
                continue
            if not has_match(value, v):
                is_match = False
        if is_match:
            return group_definition
    raise StopIteration


def has_match(value1, value2):
    if not isinstance(value1, list):
        value1 = [value1]
    if not isinstance(value2, list):
        value2 = [value2]
    for v1 in value1:
        for v2 in value2:
            if v1 == v2:
                return True
    return False


L = getLogger(__name__)

from logging import getLogger

from ..macros.iterable import find_item


class AuthorizationGuard():

    def __init__(self, configuration, safe):
        safe.constant_value_by_key = configuration.payload_by_token
        self.configuration = configuration
        self.safe = safe

    def check(self, request, permission_id, automation_definition=None):
        if not automation_definition:
            automation_definition = self.configuration
        group_definitions = automation_definition.group_definitions
        if not group_definitions:
            return True
        token = get_token(request)
        if not token:
            return False
        try:
            payload = self.safe.get(token)
        except KeyError:
            return False
        value_by_name = dict(payload, ip_address=request.remote_addr)
        try:
            group_definition = find_group_definition(
                group_definitions, value_by_name)
        except StopIteration:
            return False
        for permission_definition in group_definition.permissions:
            if permission_definition.id != permission_id:
                continue
            action = permission_definition.action
            if action == 'match':
                return define_is_match(payload)
            else:
                return True
        return False

    def put(self, payload, time_in_seconds):
        return self.safe.put(payload, time_in_seconds)


def get_token(request):
    params = request.params
    headers = request.headers
    cookies = request.cookies
    if '_token' in params:
        token = params['_token']
        request.response.set_cookie(
            'crosscompute', value=token, secure=True, httponly=True,
            samesite='strict')
    elif 'Authorization' in headers:
        try:
            token = headers['Authorization'].split(maxsplit=1)[1]
        except IndexError:
            token = ''
    elif 'crosscompute' in cookies:
        token = cookies['crosscompute']
    else:
        token = ''
    return token


def define_is_match(payload):

    def is_match(batch):
        automation_definition = batch.automation_definition
        variable_definitions = automation_definition.get_variable_definitions(
            'input')
        for name, value in payload.items():
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', name)
            except StopIteration:
                continue
            data = batch.get_data(variable_definition)
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
                L.error('"%s" is not defined in token payload', name)
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

from logging import getLogger

from ..macros.iterable import find_item
from ..macros.security import evaluate_expression


class AuthorizationGuard():

    def __init__(self, configuration, safe):
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
        for group_definition in group_definitions:
            if evaluate_expression(group_definition.expression, value_by_name):
                break
        else:
            return False
        for permission_definition in group_definition.permissions:
            if permission_definition.id != permission_id:
                continue
            expression = permission_definition.expression
            if expression:
                return define_is_match(expression, payload)
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


def define_is_match(expression, payload):

    def is_match(batch):
        automation_definition = batch.automation_definition
        variable_definitions = automation_definition.get_variable_definitions(
            'input')

        def get_value(name):
            if name in payload:
                return payload[name]
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', name)
            except StopIteration:
                raise KeyError
            data = batch.get_data(variable_definition)
            return data.get('value')

        try:
            is_match = evaluate_expression(expression, get_value)
        except NameError as e:
            L.error('"%s" failed because "%s" is not defined', expression, e)
            is_match = False
        except SyntaxError:
            L.error('"%s" failed because of a syntax error', expression)
            is_match = False
        return is_match


L = getLogger(__name__)

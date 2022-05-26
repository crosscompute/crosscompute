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
            if permission_definition.action == 'match':
                return payload
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

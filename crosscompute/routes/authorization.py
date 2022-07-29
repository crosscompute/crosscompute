from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden


class AuthorizationRoutes():

    def __init__(self, authorization_guard):
        self.guard = authorization_guard

    def includeme(self, config):
        config.include(self.configure_authorizations)

    def configure_authorizations(self, config):
        config.add_route(
            'authorizations.json', 'authorizations.json')

        config.add_view(
            self.add_authorization,
            request_method='POST',
            route_name='authorizations.json',
            renderer='json')

    def add_authorization(self, request):
        guard = self.guard
        if not guard.check(request, 'add_authorization'):
            raise HTTPForbidden
        try:
            params = request.params or request.json_body
            payload = params['payload']
            time_in_seconds = int(params['time_in_seconds'])
        except (KeyError, ValueError):
            raise HTTPBadRequest
        token = guard.put(payload, time_in_seconds)
        return {'token': token}

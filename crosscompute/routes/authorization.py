from pyramid.httpexceptions import HTTPBadRequest


class AuthorizationRoutes():

    def __init__(self, safe):
        self.safe = safe

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
        params = request.params or request.json_body
        try:
            payload = params['payload']
            time_in_seconds = int(params['time_in_seconds'])
        except (KeyError, ValueError):
            raise HTTPBadRequest
        token = self.safe.set(payload, time_in_seconds)
        return {'token': token}

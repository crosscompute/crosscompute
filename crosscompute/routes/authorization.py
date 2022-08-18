from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden

from ..routines.authorization import AuthorizationGuard


class AuthorizationRoutes():

    def __init__(self, configuration, safe):
        self.configuration = configuration
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
        # TODO: Fix to be oauth2 compliant; backport from market
        guard = AuthorizationGuard(request, self.safe)
        if not guard.check('add_authorization', self.configuration):
            raise HTTPForbidden
        try:
            params = request.params or request.json_body
            identities = params['identities']
            time_in_seconds = int(params['time_in_seconds'])
        except (KeyError, ValueError):
            raise HTTPBadRequest
        token = guard.put(identities, time_in_seconds)
        return {'token': token}

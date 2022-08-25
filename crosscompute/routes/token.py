from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden

from ..routines.authorization import AuthorizationGuard


class TokenRoutes():

    def __init__(self, configuration, safe):
        self.configuration = configuration
        self.safe = safe

    def includeme(self, config):
        config.include(self.configure_tokens)

    def configure_tokens(self, config):
        config.add_route(
            'tokens.json', 'tokens.json')

        config.add_view(
            self.add_token,
            request_method='POST',
            route_name='tokens.json',
            renderer='json')

    def add_token(self, request):
        # TODO: Fix to be oauth2 compliant; backport from market
        guard = AuthorizationGuard(request, self.safe)
        if not guard.check('add_token', self.configuration):
            raise HTTPForbidden
        try:
            params = request.params or request.json_body
            identities = params['identities']
            time_in_seconds = int(params['time_in_seconds'])
        except (KeyError, ValueError):
            raise HTTPBadRequest
        token = guard.put(identities, time_in_seconds)
        return {'access_token': token, 'token_type': 'bearer'}

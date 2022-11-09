from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden

from ..routines.authorization import AuthorizationGuard


class TokenRoutes():

    def __init__(self, configuration, safe):
        self.configuration = configuration
        self.safe = safe

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

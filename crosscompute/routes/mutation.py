from pyramid.httpexceptions import HTTPBadRequest
from time import time

from ..constants import (
    MAXIMUM_MUTATION_AGE_IN_SECONDS,
    MUTATION_ROUTE)


class MutationRoutes():

    def __init__(self, server_timestamp, infos_by_timestamp):
        self._infos_by_timestamp = infos_by_timestamp
        self._server_timestamp = server_timestamp

    def see_mutation(self, request):
        # TODO: Consider adding guard
        params = request.params
        try:
            old_timestamp = float(params.get('t', 0))
        except ValueError:
            raise HTTPBadRequest
        matchdict = request.matchdict
        uri = matchdict['uri']
        new_timestamp = time()
        infos_by_timestamp = self._infos_by_timestamp
        configurations, variables, templates, styles = [], [], [], []
        for timestamp, infos in infos_by_timestamp.copy().items():
            if new_timestamp - timestamp > MAXIMUM_MUTATION_AGE_IN_SECONDS:
                try:
                    del infos_by_timestamp[timestamp]
                except KeyError:
                    pass
            if timestamp <= old_timestamp:
                continue
            for info in infos:
                code = info['code']
                if code == 'c':
                    configurations.append({})
                elif code == 'v':
                    if uri.startswith(info['uri']):
                        # TODO: Send value or diff if authorized
                        variables.append({'id': info['id']})
                elif code == 't':
                    if uri.startswith(info['uri']):
                        templates.append({})
                elif code == 's':
                    styles.append({})
        return {
            'server_timestamp': self._server_timestamp,
            'mutation_timestamp': new_timestamp,
            'configurations': configurations,
            'variables': variables,
            'templates': templates,
            'styles': styles,
        }

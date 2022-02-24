# TODO: Define /mutations/{path}
# TODO: Trigger reload intelligently only if relevant
from ..constants import (
    MUTATIONS_ROUTE)


class MutationRoutes():

    def __init__(self, server_timestamp_object):
        self._server_timestamp_object = server_timestamp_object

    def includeme(self, config):
        config.add_route('mutations', MUTATIONS_ROUTE)

        config.add_view(
            self.see_mutations,
            route_name='mutations',
            renderer='json')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'MUTATIONS_ROUTE': MUTATIONS_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_mutations(self, request):
        return {
            'server_timestamp': self._server_timestamp_object.value,
        }

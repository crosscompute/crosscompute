from pyramid.response import Response
from time import sleep

from ..constants import ECHOES_ROUTE, PING_INTERVAL_IN_SECONDS


class EchoViews():

    def __init__(self, folder, timestamp_object):
        self.folder = folder
        self.timestamp_object = timestamp_object

    def includeme(self, config):
        config.add_route('echoes', ECHOES_ROUTE)

        config.add_view(
            self.see_echoes,
            route_name='echoes')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'ECHOES_ROUTE': ECHOES_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_echoes(self, request):
        response = Response(headerlist=[
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
        ])
        response.app_iter = self.yield_echoes()
        return response

    def yield_echoes(self):
        while True:
            sleep(PING_INTERVAL_IN_SECONDS)
            yield self.make_ping()

    def make_message(self, data):
        return f'data: {data}\n\n'.encode()

    def make_ping(self):
        return self.make_message(self.timestamp_object.value)

# TODO: Include request.path in stream view url
# TODO: Trigger reload intelligently only if relevant
from pyramid.response import Response
from time import sleep

from ..constants import (
    STREAM_PING_INTERVAL_IN_SECONDS,
    STREAMS_ROUTE)


class StreamRoutes():

    def __init__(self, timestamp_object):
        self._timestamp_object = timestamp_object

    def includeme(self, config):
        config.add_route('streams', STREAMS_ROUTE)

        config.add_view(
            self.see_streams,
            route_name='streams')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'STREAMS_ROUTE': STREAMS_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_streams(self, request):
        # TODO: Add url to queue
        response = Response(headerlist=[
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
        ])
        response.app_iter = self.yield_message()
        return response

    def yield_message(self):
        # TODO: Send queued changes
        while True:
            sleep(STREAM_PING_INTERVAL_IN_SECONDS)
            yield self.make_ping()

    def make_ping(self):
        return self.make_message(self._timestamp_object.value)

    def make_message(self, data):
        return f'data: {data}\n\n'.encode()

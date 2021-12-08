# from multiprocessing import Queue
from pyramid.response import Response
# from time import sleep, time
from time import time

from ..constants import ECHOES_ROUTE


class EchoViews():

    def __init__(self, folder):
        self.folder = folder
        # self.queues = []
        self.reset_time()

    def reset_time(self):
        self.time = time()

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
        # queue = Queue()
        # self.queues.append(queue)
        response = Response(headerlist=[
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
        ])
        # response.app_iter = self.yield_echoes(queue)
        response.app_iter = self.yield_echoes()
        return response

    def yield_echoes(self):
        yield self.make_ping()
        '''
        while True:
            # x = queue.get()
        sleep_count = 0
        while True:
            sleep(1)
            sleep_count += 1
            if sleep_count > PING_INTERVAL_IN_SECONDS:
                yield self.make_ping()
                sleep_count = 0
        '''

    def make_message(self, data):
        return f'data: {data}\n\n'.encode()

    def make_ping(self):
        return self.make_message(self.time)

# from multiprocessing import Queue
from pyramid.response import Response
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
        yield f'data: {self.time}\n\n'.encode()
        '''
        while True:
            # x = queue.get()
            # L.debug('sending refresh after change in %s', x)
            import time; time.sleep(1)
            yield f'data: {self.time}\n\n'.encode()
        '''

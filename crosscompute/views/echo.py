# from multiprocessing import Queue
from pyramid.response import Response
from time import time

from ..constants import ECHOES_ROUTE


class EchoViews():

    def __init__(self, folder):
        self.folder = folder
        # self.queue = Queue()
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
        response = Response(headerlist=[
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
        ])
        response.app_iter = self.yield_echoes()
        return response

    def yield_echoes(self):
        yield f'data: {self.time}\n\n'.encode()
        '''
        while True:
            x = self.queue.get()
            print('see_echoes', x)
            yield f'data: {x}\n\n'.encode()
        '''

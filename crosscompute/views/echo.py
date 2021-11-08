from multiprocessing import Queue
from pyramid.response import Response
from time import time


class EchoViews():

    def __init__(self, folder):
        self.folder = folder
        self.queue = Queue()
        self.time = time()

    def includeme(self, config):
        config.add_route('echoes', '/echoes')
        config.add_view(
            self.see_echoes,
            route_name='echoes')

    def see_echoes(self, request):
        response = Response(headerlist=[
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
        ])
        response.app_iter = self.yield_echoes()
        return response

    def yield_echoes(self):
        '''
        for changes in watch(self.folder):
            yield 'data: *\n\n'.encode()
        '''
        print('yield_echoes')
        yield f'data: {self.time}\n\n'.encode()
        import time
        time.sleep(3)
        yield f'data: {self.time}\n\n'.encode()

        '''
        while True:
            x = self.queue.get()
            print('see_echoes', x)
            yield f'data: {x}\n\n'.encode()
        '''

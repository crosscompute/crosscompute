from contextlib import contextmanager
from time import time


class Clock:

    def __init__(self):
        self.time_by_key = {}

    @contextmanager
    def time(self, name, t):
        d = self.time_by_key
        key_a = _get_start_key(name)
        key_b = _get_end_key(name)
        d[key_a] = t
        d[key_b] = None
        print(f'start {name} at {t}')
        yield
        d[key_a] = time()
        print(f'end {name}')

    def is_in(self, name):
        time_a = self.get_start_time(name)
        time_b = self.get_end_time(name)
        if not time_a:
            return False
        if not time_b:
            return True
        return False

    def get_start_time(self, name):
        return self.time_by_key.get(_get_start_key(name), 0)

    def get_end_time(self, name):
        return self.time_by_key.get(_get_end_key(name), 0)


def _get_start_key(name):
    return name + '<'


def _get_end_key(name):
    return '>' + name

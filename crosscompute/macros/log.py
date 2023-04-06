from contextlib import contextmanager
from time import time

from ..constants import DISK_STEP_IN_MILLISECONDS


class Clock:

    def __init__(self):
        self.time_by_key = {}

    @contextmanager
    def time(self, name):
        d = self.time_by_key
        key_a = _get_start_key(name)
        key_b = _get_end_key(name)
        d[key_a] = time()
        try:
            del d[key_b]
        except KeyError:
            pass
        yield
        d[key_b] = time()

    def is_in(self, name, t=None):
        time_a = self.get_start_time(name)
        time_b = self.get_end_time(name)
        if not time_a:
            return False
        if not time_b:
            return True
        if t:
            return time_a < t and t < time_b + DISK_STEP_IN_MILLISECONDS
        return False

    def get_start_time(self, name):
        return self.time_by_key.get(_get_start_key(name), 0)

    def get_end_time(self, name):
        return self.time_by_key.get(_get_end_key(name), 0)


def _get_start_key(name):
    return name + '<'


def _get_end_key(name):
    return '>' + name

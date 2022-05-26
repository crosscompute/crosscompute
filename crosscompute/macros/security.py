from datetime import datetime, timedelta

from invisibleroads_macros_security import make_random_string


class DictionarySafe(dict):

    def __init__(self, key_length):
        self.key_length = key_length

    def put(self, value, time_in_seconds=None):
        while True:
            key = make_random_string(self.key_length)
            try:
                self[key]
            except KeyError:
                break
        self.set(key, value, time_in_seconds)
        return key

    def set(self, key, value, time_in_seconds=None):
        self[key] = value, get_expiration_datetime(time_in_seconds)

    def get(self, key):
        value, expiration_datetime = self[key]
        if expiration_datetime and datetime.now() > expiration_datetime:
            del self[key]
            raise KeyError
        return value


def get_expiration_datetime(time_in_seconds):
    if not time_in_seconds:
        return
    return datetime.now() + timedelta(seconds=time_in_seconds)

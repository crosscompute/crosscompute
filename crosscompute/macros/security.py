from datetime import datetime, timedelta

from invisibleroads_macros_security import make_random_string


class DictionarySafe():

    def __init__(self, pack_by_key, key_length):
        self.pack_by_key = pack_by_key
        self.key_length = key_length

    def put(self, value, time_in_seconds=None):
        key_length = self.key_length
        # Use keys() until https://github.com/python/cpython/pull/17333 merges
        keys = self.pack_by_key.keys()
        while True:
            key = make_random_string(key_length)
            if key not in keys:
                break
        self.set(key, value, time_in_seconds)
        return key

    def set(self, key, value, time_in_seconds=None):
        expiration_datetime = get_expiration_datetime(time_in_seconds)
        self.pack_by_key[key] = value, expiration_datetime

    def get(self, key):
        pack_by_key = self.pack_by_key
        try:
            value, expiration_datetime = pack_by_key[key]
        except KeyError:
            raise
        else:
            if expiration_datetime and datetime.now() > expiration_datetime:
                del pack_by_key[key]
                raise KeyError(key)
        return value


def get_expiration_datetime(time_in_seconds):
    if not time_in_seconds:
        return
    return datetime.now() + timedelta(seconds=time_in_seconds)

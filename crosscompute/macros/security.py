from datetime import datetime, timedelta

from invisibleroads_macros_security import make_random_string


class DictionarySafe():

    def __init__(
            self, constant_value_by_key, variable_pack_by_key,
            variable_key_length):
        self.constant_value_by_key = constant_value_by_key
        self.variable_pack_by_key = variable_pack_by_key
        self.variable_key_length = variable_key_length

    def put(self, value, time_in_seconds=None):
        # Use keys() until https://github.com/python/cpython/pull/17333 merges
        keys = set(
            self.constant_value_by_key.keys()
        ) | set(
            self.variable_pack_by_key.keys())
        while True:
            key = make_random_string(self.variable_key_length)
            if key not in keys:
                break
        self.set(key, value, time_in_seconds)
        return key

    def set(self, key, value, time_in_seconds=None):
        expiration_datetime = get_expiration_datetime(time_in_seconds)
        self.variable_pack_by_key[key] = value, expiration_datetime

    def get(self, key):
        try:
            value, expiration_datetime = self.variable_pack_by_key[key]
        except KeyError:
            value = self.constant_value_by_key[key]
            return value
        if expiration_datetime and datetime.now() > expiration_datetime:
            del self.variable_pack_by_key[key]
            raise KeyError
        return value


def get_expiration_datetime(time_in_seconds):
    if not time_in_seconds:
        return
    return datetime.now() + timedelta(seconds=time_in_seconds)

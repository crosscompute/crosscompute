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
        if datetime.now() > expiration_datetime:
            del self[key]
            raise KeyError
        return value


def get_expiration_datetime(time_in_seconds):
    if not time_in_seconds:
        return
    return datetime.now() + timedelta(seconds=time_in_seconds)


def evaluate_expression(expression_string, value_by_name):
    # https://realpython.com/python-eval-function
    code = compile(expression_string, '<string>', 'eval')
    for name in code.co_names:
        if name not in value_by_name:
            raise NameError(f'{name} not defined')
    return eval(code, {'__builtins__': {}}, value_by_name)

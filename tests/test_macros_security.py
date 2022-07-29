from multiprocessing import Manager
from pytest import raises
from time import sleep

from crosscompute.macros.security import DictionarySafe


def test_dictionary_safe():
    with Manager() as manager:
        a = {'a': 'A'}
        b = manager.dict()
        d = DictionarySafe(a, b, variable_key_length=7)
        assert d.get('a') == 'A'
        token = d.put('B', time_in_seconds=1)
        assert d.get(token) == 'B'
        sleep(1)
        with raises(KeyError):
            d.get(token)

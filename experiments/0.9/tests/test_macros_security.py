from multiprocessing import Manager
from pytest import raises
from time import sleep

from crosscompute.macros.security import DictionarySafe


def test_dictionary_safe():
    with Manager() as manager:
        a = manager.dict()
        d = DictionarySafe(a, key_length=7)
        token = d.put('A', time_in_seconds=1)
        assert d.get(token) == 'A'
        sleep(1)
        with raises(KeyError):
            d.get(token)

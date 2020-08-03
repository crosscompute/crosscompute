from crosscompute.exceptions import DataTypeError
from crosscompute.types import DataType
from pytest import raises


class ADataType(DataType):

    @classmethod
    def load(Class, path):
        if path == 'x':
            raise Exception
        instance = Class()
        instance.path = path
        return instance

    @classmethod
    def parse(Class, x, default_value=None):
        if x == 'd':
            raise DataTypeError
        if x == 'e':
            raise Exception
        return 'a'


class BDataType(DataType):

    @classmethod
    def load(Class, path, default_value=None):
        instance = Class()
        instance.path = path
        instance.default_value = default_value
        return instance


class CDataType(DataType):

    @classmethod
    def load_for_view(Class, path):
        instance = Class()
        instance.path = path
        return instance


class TestDataType(object):

    def test_load_for_view_safely(self):
        x = ADataType.load_for_view_safely('a')
        assert x.path == 'a'

        x = ADataType.load_for_view_safely('x')
        assert x is None

        x = BDataType.load_for_view_safely('b', 'bb')
        assert x.path == 'b'
        assert x.default_value == 'bb'

        x = CDataType.load_for_view_safely('c')
        assert x.path == 'c'

    def test_parse_safely(self):
        assert ADataType.parse_safely(None) is None
        assert ADataType.parse_safely(1) is 'a'
        with raises(DataTypeError):
            ADataType.parse_safely('d')
        assert ADataType.parse_safely('e') == 'e'

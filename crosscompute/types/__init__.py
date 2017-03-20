import codecs
from abc import ABCMeta
from invisibleroads_macros.configuration import resolve_attribute
from six import add_metaclass, text_type
from stevedore.extension import ExtensionManager

from ..exceptions import DataTypeError


DATA_TYPE_BY_NAME = {}
DATA_TYPE_BY_SUFFIX = {}
RESERVED_ARGUMENT_NAMES = ['target_folder']


class DataItem(object):

    def __init__(
            self, key, value, data_type=None, file_location='', help=''):
        self.key = key
        self.value = value
        self.data_type = data_type or get_data_type(key)
        self.file_location = file_location
        self.help = help
        self.name = key.replace('_', ' ')

    def render_value(self, *args, **kw):
        x = self.data_type.render(self.value, *args, **kw)
        return '' if x is None else x


@add_metaclass(ABCMeta)
class DataType(object):
    suffixes = ()
    formats = ()
    style = None
    script = None
    template = None
    views = ()

    @classmethod
    def save(Class, path, value):
        codecs.open(path, 'w', encoding='utf-8').write(value)

    @classmethod
    def load_safely(Class, path):
        try:
            value = Class.load(path)
        except (IOError, DataTypeError):
            value = None
        return value

    @classmethod
    def load(Class, path):
        return codecs.open(path, encoding='utf-8').read()

    @classmethod
    def parse(Class, text):
        return text

    @classmethod
    def merge(Class, default_value, value):
        return value

    @classmethod
    def render(Class, value):
        return value

    @classmethod
    def get_file_name(Class):
        return '%s.%s' % (Class.suffixes[0], Class.formats[0])


class StringType(DataType):
    suffixes = 'string',
    formats = 'txt',
    template = 'crosscompute:types/string.jinja2'

    @classmethod
    def parse(Class, text):
        if not isinstance(text, str) or isinstance(text, text_type):
            return text
        return text.decode('utf-8')


def initialize_data_types(suffix_by_data_type=None):
    for x in ExtensionManager('crosscompute.types').extensions:
        data_type = x.plugin
        for suffix in data_type.suffixes:
            DATA_TYPE_BY_SUFFIX[suffix] = data_type
        DATA_TYPE_BY_NAME[x.name] = data_type
    for suffix, data_type_spec in (suffix_by_data_type or {}).items():
        data_type = resolve_attribute(data_type_spec)
        DATA_TYPE_BY_SUFFIX[suffix] = data_type


def get_data_type(key):
    for suffix, data_type in DATA_TYPE_BY_SUFFIX.items():
        if key.endswith('_' + suffix):
            return data_type
    return StringType

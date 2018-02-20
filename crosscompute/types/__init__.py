import codecs
from abc import ABCMeta
from invisibleroads_macros.configuration import resolve_attribute
from invisibleroads_macros.log import get_log, log_traceback
from six import add_metaclass, text_type
from stevedore.extension import ExtensionManager

from ..exceptions import DataTypeError


DATA_TYPE_BY_NAME = {}
DATA_TYPE_BY_SUFFIX = {}
L = get_log(__name__)
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
    suffixes = ()    # List name suffixes to reserve for this data type
    formats = ()     # Set default storage format and direct content format
    style = None     # Set style path relative to package
    script = None    # Set script path relative to package
    template = None  # Set template path relative to package
    views = ()       # List function names to register as views
    requires_value_for_path = True  # Show error if path is empty

    @classmethod
    def save(Class, path, value):
        codecs.open(path, 'w', encoding='utf-8').write(value)

    @classmethod
    def load_for_view_safely(Class, path, default_value=None):
        try:
            f = Class.load_for_view
        except AttributeError:
            f = Class.load
        function_arguments = f.__code__.co_varnames
        kw = {}
        if 'default_value' in function_arguments:
            kw['default_value'] = default_value
        try:
            value = f(path, **kw)
        except Exception:
            log_traceback(L, {'path': path, 'default_value': default_value})
            value = None
        return value

    @classmethod
    def load(Class, path, default_value=None):
        text = codecs.open(path, encoding='utf-8').read()
        return Class.parse(text, default_value)

    @classmethod
    def parse_safely(Class, x, default_value=None):
        if x is None:
            return default_value
        try:
            x = Class.parse(x, default_value)
        except DataTypeError:
            raise
        except Exception:
            log_traceback(L, {'x': x, 'default_value': default_value})
        return x

    @classmethod
    def parse(Class, x, default_value=None):
        return x

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
    def parse(Class, x, default_value=None):
        if not isinstance(x, str) or isinstance(x, text_type):
            return x
        return x.decode('utf-8')


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

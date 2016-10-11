import codecs
import logging
from abc import ABCMeta
from collections import OrderedDict
from invisibleroads_macros.log import log_traceback, parse_nested_dictionary
from invisibleroads_macros.configuration import resolve_attribute
from invisibleroads_uploads.views import get_upload, make_upload_folder
from os.path import expanduser, isabs, join, splitext
from six import add_metaclass, text_type
from stevedore.extension import ExtensionManager

from ..exceptions import DataParseError, DataTypeError


DATA_TYPE_BY_NAME = {}
DATA_TYPE_BY_SUFFIX = {}
RESERVED_ARGUMENT_NAMES = ['target_folder']
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class DataItem(object):

    def __init__(self, key, value, data_type, help_text=''):
        self.key = key
        self.value = value
        self.data_type = data_type
        self.help_text = help_text

    def format_value(self, *args, **kw):
        return self.data_type.format(self.value, *args, **kw)


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
    def format(Class, value):
        return value

    @classmethod
    def match(Class, value):
        return True


class StringType(DataType):
    formats = 'txt',
    template = 'crosscompute:types/string.jinja2'

    @classmethod
    def load(Class, path):
        return codecs.open(path, encoding='utf-8').read()

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


def get_result_arguments(
        tool_definition, raw_arguments, data_folder, user_id=0):
    d, errors = OrderedDict(), OrderedDict()
    configuration_folder = tool_definition['configuration_folder']
    for tool_argument_name in tool_definition['argument_names']:
        if tool_argument_name in raw_arguments:
            value = raw_arguments[tool_argument_name]
        elif tool_argument_name.endswith('_path'):
            tool_argument_noun = tool_argument_name[:-5]
            data_type = get_data_type(tool_argument_noun)
            default_path = join(
                configuration_folder, tool_definition[tool_argument_name],
            ) if tool_argument_name in tool_definition else None
            try:
                value = prepare_file_path(
                    data_folder, data_type, raw_arguments, tool_argument_noun,
                    user_id, default_path)
            except IOError:
                errors[tool_argument_name] = 'invalid'
                continue
            except KeyError:
                errors[tool_argument_name] = 'required'
                continue
        else:
            if tool_argument_name not in RESERVED_ARGUMENT_NAMES:
                errors[tool_argument_name] = 'required'
            continue
        d[tool_argument_name] = value
    return parse_data_dictionary_from(d, configuration_folder)


def prepare_file_path(
        data_folder, data_type, raw_arguments, tool_argument_noun, user_id,
        default_path):
    # If the client sent the content directly, save the content as a file
    for file_format in data_type.formats:
        raw_argument_name = '%s-%s' % (tool_argument_noun, file_format)
        if raw_argument_name in raw_arguments:
            file_name = '%s.%s' % (tool_argument_noun, file_format)
            file_content = raw_arguments[raw_argument_name]
            return save_upload(data_folder, user_id, file_name, file_content)

    # If the client sent the content via the user interface,
    raw_argument_name = '%s-upload' % tool_argument_noun
    if raw_argument_name in raw_arguments:
        # If the client uploaded a file, resolve the file_id
        file_id = raw_arguments[raw_argument_name]
        if file_id:
            try:
                upload = get_upload(data_folder, user_id, file_id)
            except IOError:
                raise
            else:
                return join(upload.folder, '%s.%s' % (
                    data_type.suffixes[0], data_type.formats[0]))
        # Otherwise, use the default_path for this argument
        if default_path:
            # TODO: Think of a better way to do this
            file_name = tool_argument_noun + splitext(default_path)[1]
            file_content = codecs.open(default_path, encoding='utf-8').read()
            return save_upload(data_folder, user_id, file_name, file_content)
    """
    if tool_argument_noun in raw_arguments:
        file_name = tool_argument_noun
        file_content = raw_arguments[tool_argument_noun]
        return save_upload(data_folder, user_id, file_name, file_content)
    """
    raise KeyError


def save_upload(data_folder, user_id, file_name, file_content, token_length):
    source_folder = make_upload_folder(data_folder, user_id, token_length)
    file_path = join(source_folder, file_name)
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        f.write(file_content)
    return file_path


def parse_data_dictionary(text, root_folder):
    d = parse_nested_dictionary(
        text, is_key=lambda x: ':' not in x and ' ' not in x)
    return parse_data_dictionary_from(d, root_folder)


def parse_data_dictionary_from(raw_dictionary, root_folder):
    d = make_absolute_paths(raw_dictionary, root_folder)
    errors = OrderedDict()
    for key, value in d.items():
        data_type = get_data_type(key)
        try:
            value = data_type.parse(value)
        except DataTypeError as e:
            errors[key] = text_type(e)
        except Exception as e:
            log_traceback(LOG, {'key': key, 'value': value})
            errors[key] = 'could_not_parse'
        d[key] = value
        if not key.endswith('_path'):
            continue
        noun = key[:-5]
        data_type = get_data_type(noun)
        try:
            data_type.load(value)
        except DataTypeError as e:
            errors[noun] = text_type(e)
        except IOError as e:
            log_traceback(LOG, {'key': key, 'value': value})
            errors[noun] = 'not_found'
        except Exception as e:
            log_traceback(LOG, {'key': key, 'value': value})
            errors[noun] = 'could_not_load'
    if errors:
        raise DataParseError(errors, d)
    return d


def make_absolute_paths(value_by_key, root_folder):
    d = OrderedDict()
    for key, value in OrderedDict(value_by_key).items():
        if key.endswith('_path'):
            value = expanduser(value)
            if not isabs(value):
                value = join(root_folder, value)
        d[key] = value
    return d

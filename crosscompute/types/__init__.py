import codecs
import logging
import shutil
from abc import ABCMeta
from collections import OrderedDict
from invisibleroads_macros.disk import get_file_extension
from invisibleroads_macros.log import log_traceback, parse_nested_dictionary
from invisibleroads_macros.configuration import resolve_attribute
from invisibleroads_uploads.views import get_upload, make_upload_folder
from os.path import basename, expanduser, isabs, join
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


class ResultRequest(object):

    def __init__(self):
        pass

    def get_arguments(self):
    def prepare_arguments(self):
        pass


def get_result_arguments(request, tool_definition, get_result_file_path):
    result_arguments, errors = OrderedDict(), OrderedDict()
    params, settings = request.params, request.registry.settings
    data_folder = settings['data_folder']

    file_folder = 

    configuration_folder = tool_definition['configuration_folder']
    for argument_name in tool_definition['argument_names']:
        if argument_name.endswith('_path'):
            argument_noun = argument_name[:-5]

            default_path

            try:
                value = prepare_file_path(request, argument_noun, 
                    default_path, file_folder, get_result_file_path)
            except IOError:
                errors[argument_name] = 'invalid'
                continue
            except KeyError:
                errors[argument_name] = 'required'
                continue
        elif argument_name in params:
            value = params[argument_name]
        else:
            if argument_name not in RESERVED_ARGUMENT_NAMES:
                errors[argument_name] = 'required'
            continue
        result_arguments[argument_name] = value
    if errors:
        raise DataParseError(errors, result_arguments)
    # Parse strings and validate data types
    return parse_data_dictionary_from(result_arguments, configuration_folder)


def prepare_file_path(
        argument_noun, raw_arguments, default_path, file_folder, data_folder,
        user_id, get_result_file_path):
    data_type = get_data_type(argument_noun)
    # If the client sent direct content (x_table_csv), save it
    for file_format in data_type.formats:
        raw_argument_name = '%s_%s' % (argument_noun, file_format)
        if raw_argument_name in raw_arguments:
            continue
        file_path = join(file_folder, '%s.%s' % (argument_noun, file_format))
        open(file_path, 'wb').write(raw_arguments[raw_argument_name])
        return file_path
    # Raise KeyError if client did not specify noun (x_table)
    value = raw_arguments[argument_noun].strip()
    # If the client sent empty content (x_table=''), use default
    if not value:
        if not default_path:
            raise KeyError
        file_path = join(file_folder, argument_noun + get_file_extension(
            default_path))
        shutil.copy(default_path, file_path)
        return file_path
    # If the client sent multipart content, save it
    if hasattr(value, 'file'):
        file_path = join(file_folder, argument_noun + get_file_extension(
            value.filename))
        shutil.copyfileobj(value.file, file_path)
        return file_path
    # If the client sent indirect content, find it
    if '/' in value:
        result_id, relative_path = value.split('/')
        result_file_path = get_result_file_path(
            data_folder, result_id, relative_path)
        shutil.copy(result_file_path, file_folder)
        return join(file_folder, basename(result_file_path))
    try:
        upload = get_upload(data_folder, user_id, file_id=value)
    except IOError:
        raise
    file_name = '%s.%s' % (data_type.suffixes[0], data_type.formats[0])
    shutil.move(join(upload.folder, file_name), file_folder)
    return join(file_folder, file_name)


def save_file():
    pass


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

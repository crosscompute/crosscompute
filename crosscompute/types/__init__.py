from abc import ABCMeta
from collections import OrderedDict
from invisibleroads_macros.disk import make_enumerated_folder
from invisibleroads_macros.log import parse_nested_dictionary
from os.path import dirname, expanduser, isabs, join, sep
from six import add_metaclass
from stevedore.extension import ExtensionManager

from ..configurations import RESERVED_ARGUMENT_NAMES
from ..exceptions import DataTypeError


@add_metaclass(ABCMeta)
class DataType(object):

    @classmethod
    def save(Class, path, value):
        open(path, 'wt').write(value)

    @classmethod
    def load_safely(Class, path):
        try:
            value = Class.load(path)
        except (IOError, DataTypeError):
            value = None
        return value

    @classmethod
    def load(Class, path):
        return open(path, 'rt').read()

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


class PathType(StringType):
    template = 'crosscompute:types/path.jinja2'


def get_data_type(tool_argument_name, data_type_packs=None):
    for data_type_name, data_type in data_type_packs or []:
        if tool_argument_name.endswith('_' + data_type_name):
            return data_type
    if tool_argument_name.endswith('_path'):
        return PathType
    return StringType


def get_data_type_packs():
    extension_manager = ExtensionManager('crosscompute.types')
    return sorted(zip(
        extension_manager.names(),
        (x.plugin for x in extension_manager.extensions),
    ), key=lambda pack: (-len(pack[0]), pack))


def get_relevant_data_types(data_type_packs, data_type_keys):
    data_types = []
    for data_type_key in data_type_keys:
        if data_type_key.endswith('_path'):
            data_type_key = data_type_key[:-5]
        data_types.append(get_data_type(data_type_key, data_type_packs))
    if hasattr(data_type_keys, 'values'):
        for x in data_type_keys.values():
            if hasattr(x, 'keys'):
                data_types.extend(get_relevant_data_types(data_type_packs, x))
    return list(set(data_types).difference([StringType]))


def get_result_arguments(
        tool_definition, raw_arguments, data_type_packs,
        data_folder=join(sep, 'tmp')):
    d, errors = {}, []
    for tool_argument_name in tool_definition['argument_names']:
        if tool_argument_name in raw_arguments:
            value = raw_arguments[tool_argument_name]
        elif tool_argument_name.endswith('_path'):
            tool_argument_noun = tool_argument_name[:-5]
            data_type = get_data_type(tool_argument_noun, data_type_packs)
            try:
                value = prepare_file_path(
                    data_folder, data_type, raw_arguments, tool_argument_noun)
            except KeyError:
                errors.append((tool_argument_name, 'required'))
                continue
        else:
            if tool_argument_name not in RESERVED_ARGUMENT_NAMES:
                errors.append((tool_argument_name, 'required'))
            continue
        d[tool_argument_name] = value
    d, more_errors = parse_data_dictionary_from(
        d, data_type_packs, dirname(tool_definition['configuration_path']))
    errors.extend(more_errors)
    if errors:
        raise DataTypeError(*errors)
    return d


def prepare_file_path(
        data_folder, data_type, raw_arguments, tool_argument_noun):
    for file_format in data_type.formats:
        raw_argument_name = '%s_%s' % (tool_argument_noun, file_format)
        if raw_argument_name in raw_arguments:
            break
    else:
        raise KeyError
    file_content = raw_arguments[raw_argument_name]
    file_name = '%s.%s' % (tool_argument_noun, file_format)
    upload_folder = make_enumerated_folder(join(data_folder, 'uploads'))
    file_path = join(upload_folder, file_name)
    with open(file_path, 'w') as f:
        f.write(file_content)
    return file_path


def parse_data_dictionary_from(
        raw_dictionary, data_type_packs, configuration_folder):
    d, errors = OrderedDict(), []
    for key, value in OrderedDict(raw_dictionary).items():
        data_type = get_data_type(key, data_type_packs)
        try:
            value = data_type.parse(value)
        except DataTypeError as e:
            errors.append((key, str(e)))
        d[key] = value
        if not key.endswith('_path'):
            continue
        noun = key[:-5]
        data_type = get_data_type(noun, data_type_packs)
        value = expanduser(value)
        if not isabs(value):
            value = join(configuration_folder, value)
        try:
            data_type.load(value)
        except IOError as e:
            errors.append((noun, 'not_found'))
        except DataTypeError as e:
            errors.append((noun, str(e)))
    return d, errors


def parse_data_dictionary(text, data_type_packs, configuration_folder):
    d = parse_nested_dictionary(text, is_key=lambda x: ':' not in x)
    return parse_data_dictionary_from(d, data_type_packs, configuration_folder)

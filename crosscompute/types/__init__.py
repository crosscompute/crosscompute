from abc import ABCMeta
from collections import OrderedDict
from invisibleroads_macros.disk import make_enumerated_folder
from invisibleroads_macros.log import parse_nested_dictionary
from os.path import dirname, expanduser, isabs, join, sep
from six import add_metaclass
from stevedore.extension import ExtensionManager

from ..configurations import RESERVED_ARGUMENT_NAMES


@add_metaclass(ABCMeta)
class DataType(object):

    def save(self, path, value):
        open(path, 'wt').write(value)

    def load_safely(self, path):
        try:
            value = self.load(path)
        except (IOError, TypeError):
            value = None
        return value

    def load(self, path):
        return open(path, 'rt').read()

    def parse(self, text):
        return text

    def format(self, value):
        return value

    def match(self, value):
        return True


class StringType(DataType):
    template = 'crosscompute:types/string.jinja2'
    file_formats = ['txt']


class PathType(DataType):
    template = 'crosscompute:types/path.jinja2'
    file_formats = ['txt']


def get_data_type(tool_argument_name, data_type_packs=None):
    for data_type_name, data_type in data_type_packs or []:
        if tool_argument_name.endswith('_' + data_type_name):
            return data_type
    if tool_argument_name.endswith('_path'):
        return PathType()
    return StringType()


def get_data_type_packs():
    extension_manager = ExtensionManager(
        'crosscompute.types', invoke_on_load=True)
    return sorted(zip(
        extension_manager.names(),
        (x.obj for x in extension_manager.extensions),
    ), key=lambda pack: (-len(pack[0]), pack))


def get_result_arguments(
        tool_definition, raw_arguments, data_type_packs,
        data_folder=join(sep, 'tmp'), user_id=0):
    d, errors = {}, []
    for tool_argument_name in tool_definition['argument_names']:
        if tool_argument_name in raw_arguments:
            value = raw_arguments[tool_argument_name]
        elif tool_argument_name.endswith('_path'):
            tool_argument_noun = tool_argument_name[:-5]
            data_type = get_data_type(tool_argument_noun, data_type_packs)
            try:
                value = prepare_file_path(
                    data_folder, data_type, raw_arguments, tool_argument_noun,
                    user_id)
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
        raise TypeError(*errors)
    return d


def prepare_file_path(
        data_folder, data_type, raw_arguments, tool_argument_noun, user_id):
    for file_format in data_type.file_formats:
        raw_argument_name = '%s_%s' % (tool_argument_noun, file_format)
        if raw_argument_name in raw_arguments:
            break
    else:
        raise KeyError
    file_content = raw_arguments[raw_argument_name]
    file_name = '%s.%s' % (tool_argument_noun, file_format)
    upload_folder = make_enumerated_folder(join(
        data_folder, 'uploads'), first_index=1 if user_id else 0)
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
        except TypeError as e:
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
        except TypeError as e:
            errors.append((noun, str(e)))
    return d, errors


def parse_data_dictionary(text, data_type_packs, configuration_folder):
    return parse_data_dictionary_from(parse_nested_dictionary(
        text), data_type_packs, configuration_folder)

from abc import ABCMeta
from invisibleroads_macros.disk import make_enumerated_folder
from invisibleroads_macros.log import (
    format_summary, parse_nested_dictionary)
from os.path import join, sep
from six import add_metaclass
from stevedore.extension import ExtensionManager


@add_metaclass(ABCMeta)
class DataType(object):

    def save(self, path, value):
        open(path, 'wt').write(value)

    def load(self, path):
        return open(path, 'rt').read()

    def parse(self, text):
        return text

    def format(self, value):
        return value


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
        tool_argument_names, raw_arguments, data_type_packs,
        data_folder=join(sep, 'tmp'), user_id=0):
    d, error_packs = {}, []
    for tool_argument_name in tool_argument_names:
        is_path = tool_argument_name.endswith('_path')
        if tool_argument_name in raw_arguments:
            value = raw_arguments[tool_argument_name]
            if is_path:
                tool_argument_noun = tool_argument_name[:-5]
                data_type = get_data_type(tool_argument_noun, data_type_packs)
                try:
                    data_type.load(value)
                except TypeError as e:
                    error_packs.append((tool_argument_noun, str(e)))
                d[tool_argument_name] = value
            else:
                data_type = get_data_type(tool_argument_name, data_type_packs)
                try:
                    d[tool_argument_name] = data_type.parse(value)
                except TypeError as e:
                    error_packs.append((tool_argument_name, str(e)))
        elif tool_argument_name.endswith('_path'):
            tool_argument_noun = tool_argument_name[:-5]
            data_type = get_data_type(tool_argument_noun, data_type_packs)
            try:
                d[tool_argument_name] = prepare_file_path(
                    data_folder, data_type, raw_arguments, tool_argument_noun,
                    user_id)
            except (KeyError, TypeError) as e:
                error_packs.append((tool_argument_noun, str(e)))
    if error_packs:
        raise TypeError(*error_packs)
    return d


def prepare_file_path(
        data_folder, data_type, raw_arguments, tool_argument_noun, user_id):
    for file_format in data_type.file_formats:
        raw_argument_name = '%s_%s' % (tool_argument_noun, file_format)
        if raw_argument_name in raw_arguments:
            break
    else:
        raise KeyError('required')
    file_content = raw_arguments[raw_argument_name]
    file_name = '%s.%s' % (tool_argument_noun, file_format)
    upload_folder = make_enumerated_folder(join(
        data_folder, 'uploads'), first_index=1 if user_id else 0)
    file_path = join(upload_folder, file_name)
    with open(file_path, 'w') as f:
        f.write(file_content)
    data_type.load(file_path)
    return file_path


def format_data_dictionary(value_by_key, data_type_packs, censored=False):
    suffix_format_packs = [
        (suffix, data_type.format) for suffix, data_type in data_type_packs]
    return format_summary(value_by_key, suffix_format_packs, censored=censored)


def parse_data_dictionary(text, data_type_packs):
    suffix_parse_packs = [
        (suffix, data_type.parse) for suffix, data_type in data_type_packs]
    return parse_nested_dictionary(text, suffix_parse_packs)

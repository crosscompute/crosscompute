from abc import ABCMeta
from invisibleroads_macros.disk import make_enumerated_folder
from invisibleroads_macros.log import (
    format_nested_dictionary, parse_nested_dictionary)
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


def prepare_result_arguments(
        tool_argument_names, raw_arguments, data_type_packs,
        data_folder=join(sep, 'tmp'), user_id=0):
    d, error_packs = {'_upload_keys': []}, []
    for tool_argument_name in tool_argument_names:
        if tool_argument_name in raw_arguments:
            value = raw_arguments[tool_argument_name]
            data_type = get_data_type(tool_argument_name, data_type_packs)
            try:
                d[tool_argument_name] = data_type.parse(value)
            except TypeError as e:
                error_packs.append((tool_argument_name, str(e)))
        elif tool_argument_name.endswith('_path'):
            tool_argument_noun = tool_argument_name[:-5]
            data_type = get_data_type(tool_argument_noun, data_type_packs)
            for file_format in data_type.file_formats:
                raw_argument_name = '%s_%s' % (tool_argument_noun, file_format)
                if raw_argument_name not in raw_arguments:
                    continue
                target_path = _save_upload(data_folder, '%s.%s' % (
                    tool_argument_noun, file_format,
                ), raw_arguments[raw_argument_name], user_id)
                try:
                    data_type.load(target_path)
                except TypeError as e:
                    error_packs.append((raw_argument_name, str(e)))
                d[tool_argument_name] = target_path
                d['_upload_keys'].append(tool_argument_name)
                break
    if error_packs:
        raise TypeError(*error_packs)
    return d


def format_data_dictionary(value_by_key, data_type_packs):
    suffix_format_packs = [
        (suffix, data_type.format) for suffix, data_type in data_type_packs]
    return format_nested_dictionary(value_by_key, suffix_format_packs)


def parse_data_dictionary(text, data_type_packs):
    suffix_parse_packs = [
        (suffix, data_type.parse) for suffix, data_type in data_type_packs]
    return parse_nested_dictionary(text, suffix_parse_packs)


def _save_upload(data_folder, file_name, file_content, user_id):
    upload_folder = make_enumerated_folder(join(
        data_folder, 'uploads'), first_index=1 if user_id else 0)
    target_path = join(upload_folder, file_name)
    with open(target_path, 'w') as target_file:
        target_file.write(file_content)
    return target_path

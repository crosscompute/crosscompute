from os.path import splitext
from ruamel.yaml import YAML

from ..exceptions import CrossComputeError


def get_configuration_format(path):
    file_extension = splitext(path)[1]
    try:
        configuration_format = {
            '.cfg': 'ini',
            '.ini': 'ini',
            '.toml': 'toml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }[file_extension]
    except KeyError:
        raise CrossComputeError(
            f'{file_extension} format not supported for configuration'.strip())
    return configuration_format


def save_raw_configuration_yaml(configuration_path, configuration):
    yaml = YAML()
    return yaml.dump(configuration, open(configuration_path, 'wt'))


def load_raw_configuration_yaml(configuration_path, with_comments=False):
    yaml = YAML(typ='rt' if with_comments else 'safe')
    return yaml.load(open(configuration_path, 'rt'))


def apply_functions(value, function_names, function_by_name):
    for function_name in function_names:
        function_name = function_name.strip()
        if not function_name:
            continue
        try:
            f = function_by_name[function_name]
        except KeyError:
            raise
        value = f(value)
    return value

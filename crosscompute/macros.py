from math import isnan
from os import environ


def get_environment_value(name, default=None, is_required=False):
    try:
        value = environ[name]
    except KeyError:
        if is_required:
            exit(f'{name} is required in the environment')
        value = default
    return value


def sanitize_json_value(value):
    if isinstance(value, dict):
        return {
            sanitize_json_value(k): sanitize_json_value(v)
            for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(_) for _ in value]
    if isinstance(value, str):
        return value
    return None if value is None or isnan(value) else value

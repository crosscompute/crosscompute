from math import isnan
from os import environ
from os.path import split


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


def parse_number(raw_value):
    try:
        value = int(raw_value)
    except ValueError:
        value = float(raw_value)
    return value


def split_path(path):
    pieces = []
    chunk = path
    while True:
        chunk, piece = split(chunk)
        if not piece:
            break
        pieces.append(piece)
    return pieces[::-1]

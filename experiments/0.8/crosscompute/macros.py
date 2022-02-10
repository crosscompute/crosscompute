from invisibleroads_macros_text import compact_whitespace
from math import isnan
from os.path import split
from packaging.version import parse as parse_version


def sanitize_name(name):
    return compact_whitespace(''.join(
        _ if is_valid_name_character(_) else ' ' for _ in name))


def is_valid_name_character(x):
    if x.isalpha() or x.isdigit():
        return True
    if x in [' ', '-', '_', ',', '.']:
        return True
    return False


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


def parse_number_safely(raw_value):
    # TODO: Consider moving to invisibleroads_macros_configuration
    try:
        value = parse_number(raw_value)
    except (TypeError, ValueError):
        value = raw_value
    return value


def parse_number(raw_value):
    # TODO: Consider moving to invisibleroads_macros_configuration
    try:
        integer_value = int(raw_value)
    except ValueError:
        integer_value = None
    try:
        float_value = float(raw_value)
    except ValueError:
        float_value = None
    if integer_value is None and float_value is None:
        raise ValueError
    elif integer_value != float_value:
        value = float_value
    else:
        value = integer_value
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


def is_compatible_version(target_version_name, source_version_name):
    target_version = parse_version(target_version_name)
    source_version = parse_version(source_version_name)
    try:
        has_same_major = target_version.major == source_version.major
        has_same_minor = target_version.minor == source_version.minor
        has_same_micro = target_version.micro == source_version.micro
    except AttributeError:
        is_compatible = target_version_name == source_version_name
    else:
        is_compatible = has_same_major and has_same_minor and has_same_micro
    return is_compatible


def get_plain_value(x):
    if hasattr(x, 'items'):
        return {k: get_plain_value(v) for k, v in x.items()}
    if hasattr(x, 'append'):
        return [get_plain_value(_) for _ in x]
    return x

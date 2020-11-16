import sys
from math import isnan
from os import environ
from os.path import split
from packaging.version import parse as parse_version


def get_environment_value(name, default=None):
    try:
        value = environ[name]
    except KeyError:
        if default is None:
            sys.exit(f'{name} is required in the environment')
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


def parse_number_safely(raw_value):
    try:
        value = parse_number(raw_value)
    except (TypeError, ValueError):
        value = raw_value
    return value


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

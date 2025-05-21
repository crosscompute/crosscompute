from importlib import import_module
from packaging import version


def import_attribute(attribute_string):
    module_string, attribute_name = attribute_string.rsplit('.', maxsplit=1)
    return getattr(import_module(module_string), attribute_name)


def is_equivalent_version(version_a, version_b, version_depth=3):
    normalized_version_a = normalize_version(version_a, version_depth)
    normalized_version_b = normalize_version(version_b, version_depth)
    return normalized_version_a == normalized_version_b


def normalize_version(v, depth=3):
    return version.parse(v).release[:depth]

from importlib import import_module


def import_attribute(attribute_string):
    module_string, attribute_name = attribute_string.rsplit('.', maxsplit=1)
    return getattr(import_module(module_string), attribute_name)

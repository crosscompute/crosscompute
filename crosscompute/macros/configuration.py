import logging
from os import environ


def get_environment_value(key, default=None):
    try:
        value = environ[key]
    except KeyError:
        logging.error(f'{key} is not defined in the environment')
        if default is None:
            raise
        value = default
    return value

from logging import getLogger
from os import environ


L = getLogger(__name__)


def get_environment_value(key, default=None):
    try:
        value = environ[key]
    except KeyError:
        L.error(f'{key} is not defined in the environment')
        if default is None:
            raise
        value = default
    return value

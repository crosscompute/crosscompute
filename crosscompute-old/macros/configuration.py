from logging import getLogger
from os import environ


L = getLogger(__name__)


def get_environment_value(key, default=None):
    try:
        value = environ[key]
    except KeyError:
        L.error('%s is not defined in the environment', key)
        if default is None:
            raise
        value = default
    return value

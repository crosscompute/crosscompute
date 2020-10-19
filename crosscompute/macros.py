from os import environ


def get_environment_value(name, default=None, is_required=False):
    try:
        value = environ[name]
    except KeyError:
        if is_required:
            exit(f'{name} is required in the environment')
        value = default
    return value

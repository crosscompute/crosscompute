from os import environ


def get_token():
    variable_name = 'CROSSCOMPUTE_TOKEN'
    try:
        token = environ[variable_name]
    except KeyError:
        exit(f'Expected environment variable: {variable_name}')
    return token

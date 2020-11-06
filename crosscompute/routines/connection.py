from sseclient import SSEClient

from ..constants import CLIENT_URL, SERVER_URL
from ..macros import get_environment_value


def get_client_url():
    return get_environment_value('CROSSCOMPUTE_CLIENT', CLIENT_URL)


def get_server_url():
    return get_environment_value('CROSSCOMPUTE_SERVER', SERVER_URL)


def get_token():
    return get_environment_value('CROSSCOMPUTE_TOKEN')


def get_resource_url(server_url, resource_name, resource_id=None):
    url = server_url + '/' + resource_name
    if resource_id:
        url += '/' + resource_id
    return url + '.json'


def get_echoes_client(server_url, token):
    url = f'{server_url}/echoes/{token}.json'
    return SSEClient(url)

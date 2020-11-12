import requests
from sseclient import SSEClient

from ..constants import (
    BASH_CONFIGURATION_TEXT,
    CLIENT_URL,
    SERVER_URL)
from ..exceptions import (
    CrossComputeConnectionError,
    CrossComputeExecutionError)
from ..macros import (
    get_environment_value)


def get_bash_configuration_text():
    return BASH_CONFIGURATION_TEXT.format(
        client_url=get_client_url(),
        server_url=get_server_url(),
        token=get_token('YOUR-TOKEN'))


def fetch_resource(
        resource_name, resource_id=None, method='GET', data=None,
        server_url=None, token=None):
    f = getattr(requests, method.lower())
    server_url = server_url if server_url else get_server_url()
    url = get_resource_url(server_url, resource_name, resource_id)
    token = token if token else get_token()
    headers = {'Authorization': 'Bearer ' + token}
    kw = {}
    if data is not None:
        kw['json'] = data
    try:
        response = f(url, headers=headers, **kw)
    except requests.ConnectionError:
        raise CrossComputeConnectionError({
            'url': 'could not connect to server ' + url})
    status_code = response.status_code
    d = {'statusCode': status_code}
    if status_code == 401:
        d['statusDescription'] = 'unauthorized'
        d['statusHelp'] = 'please check your server url and token'
        d['bashEnvironment'] = get_bash_configuration_text()
        raise CrossComputeConnectionError(d)
    elif status_code != 200:
        try:
            response_json = response.json()
            if response_json:
                d.update(response_json)
        except ValueError:
            d['responseContent'] = response.content.decode('utf-8')
        raise CrossComputeExecutionError(d)
    return response.json()


def get_client_url():
    return get_environment_value('CROSSCOMPUTE_CLIENT', CLIENT_URL)


def get_server_url():
    return get_environment_value('CROSSCOMPUTE_SERVER', SERVER_URL)


def get_token(default=None):
    return get_environment_value('CROSSCOMPUTE_TOKEN', default)


def get_resource_url(server_url, resource_name, resource_id=None):
    url = server_url + '/' + resource_name
    if resource_id:
        url += '/' + resource_id
    return url + '.json'


def get_echoes_client():
    server_url = get_server_url()
    token = get_token()
    url = f'{server_url}/echoes/{token}.json'
    try:
        client = SSEClient(url)
    except Exception:
        raise CrossComputeConnectionError({
            'url': 'could not connect to echoes ' + url})
    return client

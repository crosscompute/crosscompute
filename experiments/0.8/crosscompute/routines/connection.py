import json
import requests

from ..constants import (
    BASH_CONFIGURATION_TEXT,
    CLIENT_URL,
    SERVER_URL)
from ..exceptions import (
    CrossComputeConnectionError,
    CrossComputeExecutionError,
    CrossComputeImplementationError,
    CrossComputeKeyboardInterrupt)
from ..macros import (
    get_environment_value)


def fetch_resource(
        resource_name, resource_id=None, method='GET', data=None,
        server_url=None, token=None):
    f = getattr(requests, method.lower())
    server_url = server_url if server_url else get_server_url()
    url = get_resource_url(server_url, resource_name, resource_id)
    token = token if token else get_token()
    kw = {} if data is None else {'json': data}
    try:
        response = f(url, headers={'Authorization': 'Bearer ' + token}, **kw)
    except requests.ConnectionError:
        raise CrossComputeConnectionError({
            'url': 'could not connect to server ' + url})
    status_code = response.status_code
    d = {'url': url, 'token': token, 'statusCode': status_code}
    if status_code in [401, 403]:
        d['statusHelp'] = 'please check your server url and token'
        raise CrossComputeConnectionError(d)
    try:
        response_json = response.json()
    except ValueError:
        d['statusHelp'] = 'could not parse response as json'
        d['responseContent'] = response.content.decode('utf-8')
        raise CrossComputeConnectionError(d)
    if status_code != 200:
        if response_json:
            d.update(response_json)
        raise (
            CrossComputeExecutionError if status_code == 400 else
            CrossComputeImplementationError)(d)
    return response_json

# import requests
from invisibleroads.scripts import Script
# from urllib.parse import urlparse as parse_url

from ...constants import HOST
from ...routines import get_token


class AddToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('--host', default=HOST)
        argument_subparser.add_argument('path')

    def run(self, args, argv):
        host = args.host
        token = get_token()
        path = args.path
        return run(host, token, path)


def run(host, token, path):
    # url = host + '/tools.json'
    # headers = {'Authorization': 'Bearer ' + token}
    d = get_request_dictionary(path)
    from IPython.lib.pretty import pprint
    pprint(d)
    # response = requests.post(url, headers=headers, json=d)
    # return response.json()


def get_request_dictionary(path, slug=None):
    # if is_uri(path):
    #   return {'uri': path}
    pass


'''
def is_uri(x):
    for prefix in ('git@', 'http://', 'https://'):
        if x.startswith(prefix):
            return True
    return False
'''

import requests
from argparse import ArgumentParser
from IPython.lib.pretty import pprint
from os import environ


def run(host, token, configuration_text):
    url = host + '/tools.json'
    headers = {'Authorization': 'Bearer ' + token}
    d = {'configurationText': configuration_text}
    response = requests.post(url, headers=headers, json=d)
    return response.json()


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        '--host', default='https://services.projects.crosscompute.com')
    argument_parser.add_argument('configuration_path')
    args = argument_parser.parse_args()
    host = args.host
    token = environ['CROSSCOMPUTE_TOKEN']
    configuration_path = args.configuration_path
    configuration_text = open(configuration_path, 'rt').read()
    d = run(
        host,
        token,
        configuration_text)
    pprint(d)

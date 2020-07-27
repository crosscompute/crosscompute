from os import environ
import time
from sseclient import SSEClient
import requests

services_url = environ['CROSSCOMPUTE_SERVICES_URL']
# Get echoes token
echoes_token = environ['CROSSCOMPUTE_ECHOES_TOKEN']
# Get chores token
chores_token = environ['CROSSCOMPUTE_CHORES_TOKEN']
patch_token = ''

echoes_url = services_url + '/echoes.json'
echoes_headers = {'Authorization': 'Bearer ' + echoes_token}
echoes_client = SSEClient(echoes_url, headers=echoes_headers)
chores_url = services_url + '/chores.json'
chores_headers = {'Authorization': 'Bearer ' + chores_token}
patch_headers = {'Authorization': 'Bearer ' + patch_token}

# For each echo,
for message in echoes_client:
    print(message.__dict__)
    print(message.__dict__.keys())
    print(message.id)
    print(message.event)
    print(message.data)
    print(message.retry)
    # Get chore
    # Sleep
    # Send update
    if message.event == 'results':
        chore = requests.get(chores_url, headers=chores_headers)
        print(chore.json())
        print(chore.status_code)
        # Get result data from chore
        result_id = chore['results'][0]['id']
        patch_token = 'dummy'
        payload = {
            'progress': 100,
            'outputVariableDataById': {
                'c': {'value': 7},
            },
            'logVariableDataById': {},
            'traceVariableDataById': {},
        }
        # Sleep
        time.sleep(5)
        # Send update
        patch_url = services_url + '/results/' + result_id + '.json'
        patch_res = requests.patch(
            url=patch_url, headers=patch_headers, json=payload)
        print(patch_res.json())
'''
chore_headers = {'Authorization': 'Bearer ' + chore_token}
messages =
for message in messages:
    print(message.__dict__)
    print(message)

Results:
{'results': [{'id': 'mjDbaf4q', 'name': 'Result 1', 'progress': 0, 'tool': {'id': 'OsDQIhc4', 'version': {'id':
 'nZhtYEAv'}}, 'inputVariableDataById': {'a': {'value': 1}, 'b': {'value': 2}}, 'outputVariableDataById': {'c':
  3}}]}
'''

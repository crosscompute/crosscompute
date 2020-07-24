import os
from sseclient import SSEClient

services_url = os.environ.get('CROSSCOMPUTE_SERVICES_URL')
echo_token = os.environ.get('CROSSCOMPUTE_ECHO_TOKEN')
chore_token = os.environ.get('CROSSCOMPUTE_CHORE_TOKEN')
echo_headers = {'Authorization': 'Bearer ' + echo_token}
chore_headers = {'Authorization': 'Bearer ' + chore_token}


echoes_url = services_url + '/echoes.json'
messages = SSEClient(echoes_url, headers=echo_headers)
for message in messages:
    print(message.__dict__)
    print(message)

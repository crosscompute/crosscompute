from os import environ
from sseclient import SSEClient


services_url = environ['CROSSCOMPUTE_SERVICES_URL']
# Get echoes token
echoes_token = environ['CROSSCOMPUTE_ECHOES_TOKEN']
# Get chores token
chores_token = environ['CROSSCOMPUTE_CHORES_TOKEN']


echoes_url = services_url + '/echoes.json'
headers = {'Authorization': 'Bearer ' + echoes_token}
echoes_client = SSEClient(echoes_url, headers=headers)


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


'''
chore_headers = {'Authorization': 'Bearer ' + chore_token}
messages =
for message in messages:
    print(message.__dict__)
    print(message)
'''

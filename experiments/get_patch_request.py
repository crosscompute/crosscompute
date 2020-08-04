"""
Worker using token to listen for echoes and get chores
"""
import requests
from sseclient import SSEClient


echoes_url = 'http://localhost:5500/echoes.json'
echoes_token = 'ABCDEFGHI'
echoes_headers = {'Authorization': 'Bearer ' + echoes_token}
echoes_client = SSEClient(echoes_url, headers=echoes_headers)
chores_token = echoes_token
chores_url = 'http://localhost:5000/chores.json'
chores_headers = {'Authorization': 'Bearer ' + chores_token}
patch_token = ''
result_id = 'xyz'
patch_url = f'/results/{result_id}.json'

# GET /echoes.json
for message in echoes_client:

    '''
    id: 1596466072131
    event: r
    data: {"#":"abc","u":"x","p":"x","t":"x","v":"x"}


    {"results": {"id": "abc", "inputVariableDataById": {"a": 1, "b": 2}, "token": "xyz"}}

    chore = {
        'results': {
            'id': 'abc',
            'inputVariableDataById': {
                'a': 1,
                'b': 2,
            },
            'token': 'xyz',
        },
    }



    '''

    if message.event == 'r':
        print(message)
        res = requests.get(chores_url, chores_headers)
        print(res.content)
        chore = res.json()
        results_id = chore['results']['id']
        # print(f'results_id = {results_id}')
        # GET /chores.json
        # PATCH /results/{results_id}.json
        patch_data = {
            'result token': 'xyz',
            'progress': 'in progress',
            'outputVariableDataById': 'some data',
            'logVariableDataById': 'a',
            'traceVariableDataById': '1',
        }
        patch_headers = {
            'Authorization': 'Bearer ' + chore['results']['token'],
        }
        patch = requests.patch(
            patch_url, json=patch_data, headers=patch_headers)
        print(patch.content)

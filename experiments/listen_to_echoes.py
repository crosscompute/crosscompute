import os
from sseclient import SSEClient
import requests

url = os.environ.get('CROSSCOMPUTE_SERVICES_URL')
echo_token = os.environ.get('CROSSCOMPUTE_ECHO_TOKEN')
task_token = os.environ.get('CROSSCOMPUTE_TASK_TOKEN')
echo_headers = {'Authorization': echo_token}
task_headers = {'Authorization': task_headers}


msgs = SSEClient(url, headers=echo_headers)
msg_list = [m for m in msgs]
res = requests.get(url, task_headers)
print(res.content)
    
        

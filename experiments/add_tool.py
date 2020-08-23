configuration_path = '~/Projects/crosscompute-platform/crosscompute-examples/add-numbers/.crosscompute.yml'
response = requests.post(url, headers=headers, json={
    'configurationText': 'hey',
})
print(d['id'])

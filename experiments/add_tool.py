import requests
# from argparse import ArgumentParser


token = 'abc'
headers = {
    'Authorization': 'Bearer ' + token,
}
configuration_path = '~/Projects/crosscompute-platform/crosscompute-examples/add-numbers/.crosscompute.yml'
base_url = 'https://services.projects.crosscompute.com'
url = base_url + '/tools.json'


response = requests.post(url, headers=headers, json={
    'configurationText': 'hey',
})
d = response.json()
print(d['id'])


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument()

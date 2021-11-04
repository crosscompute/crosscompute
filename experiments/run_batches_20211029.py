import json
import re
import yaml
from collections import defaultdict
from invisibleroads_macros_text.keys import normalize_key
from markdown import markdown
from os import getenv, makedirs
from os.path import basename, dirname, join, relpath
from pyramid.config import Configurator
from sys import argv
from wsgiref.simple_server import make_server


'''
command_environment = {
    # 'VIRTUAL_ENV': getenv('VIRTUAL_ENV', ''),
}
'''


# TODO: Do both output and input
batch_configuration = {'input': {'variables': []}, 'output': {'variables': []}}

variable_definitions_by_path = defaultdict(list)
output_variable_definitions = configuration['output']['variables']
for d in output_variable_definitions:
    path = d['path']
    variable_definitions_by_path[path].append(d)
variable_definitions_by_path = dict(variable_definitions_by_path)

# Set output variable data
for (
    relative_path,
    variable_definitions,
) in variable_definitions_by_path.items():
    # TODO: Fix
    if not relative_path.endswith('.json'):
        continue

    # TODO: Check path extension
    # print(configuration_folder)
    # print(output_folder)
    path = join(configuration_folder, output_folder, relative_path)
    # print(path)
    data = json.load(open(path, 'rt'))
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        variable_data = data[variable_id]
        batch_configuration['output']['variables'].append({
            'id': variable_id,
            'data': variable_data,
        })

for variable_definition in variable_definitions:
    variable_id = variable_definition['id']
    variable_view = variable_definition['view']
    variable_path = variable_definition['path']
    print(variable_id, variable_view, variable_path)
    if variable_view == 'image':
        variable_data = variable_path
        batch_configuration['output']['variables'].append({
            'id': variable_id,
            'data': variable_data,
        })

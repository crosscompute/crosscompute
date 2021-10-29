# TODO: Run batches in separate thread
import json
import re
import subprocess
import yaml
from collections import defaultdict
from markdown import markdown
from os import getenv, makedirs
from os.path import dirname, join, relpath
from pyramid.config import Configurator
# from pyramid.response import Response
from sys import argv
from wsgiref.simple_server import make_server


VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')


# Get configuration path and folder
configuration_path = argv[1]
configuration_folder = dirname(configuration_path)
# print(configuration_folder)
# Load configuration
configuration = yaml.safe_load(open(configuration_path, 'rt'))
# Get script configuration
script_configuration = configuration['script']
script_folder = script_configuration['folder']
command_string = script_configuration['command']
# Get batch configurations
batch_configurations = configuration['batches']
batch_configuration = batch_configurations[0]
# print(batch_configuration)
# Run each batch
batch_folder = batch_configuration['folder']
# TODO: Consider renaming to relative_input_folder
input_folder = join(batch_folder, 'input')
output_folder = join(batch_folder, 'output')
try:
    makedirs(output_folder)
except OSError:
    pass
command_environment = {
    'PATH': getenv('PATH', ''),
    # 'VIRTUAL_ENV': getenv('VIRTUAL_ENV', ''),
    'CROSSCOMPUTE_INPUT_FOLDER': relpath(input_folder, script_folder),
    'CROSSCOMPUTE_OUTPUT_FOLDER': relpath(output_folder, script_folder),
}
subprocess.run(
    command_string,
    shell=True,
    cwd=configuration_folder,
    env=command_environment)


# TODO: Do both output and input
batch_configuration = {'input': {'variables': []}, 'output': {'variables': []}}
batch_configuration

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


# print('AA', variable_definitions)
variable_definitions = configuration['output']['variables']


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


batch_variable_definitions = batch_configuration['output']['variables']
variable_data_by_id = {_['id']: _['data'] for _ in batch_variable_definitions}
variable_data_by_id


def render_variable_from_regex_match(match):
    matching_text = match.group(0)
    print(matching_text)
    variable_id = match.group(1)
    try:
        # TODO: Do both output and input
        variable_data = variable_data_by_id[variable_id]
    except KeyError:
        print(variable_id, variable_data_by_id)
        print('UHOH')
        return matching_text
    '''
    replacement_text = "<input
            class='input {variable_id}'
            type='number' value='{variable_data}'>".format(
        variable_id=variable_id,
        variable_data=variable_data)
    '''
    image_url = '/a/randomize-histograms/b/a/o/' + variable_data
    replacement_text = f"<img src='{image_url}'>"
    return replacement_text


# Define routes and views
def home(request):
    automation_configurations = [{
        'url': '/a/randomize-histograms',
    }]
    return {
        'automation_configurations': automation_configurations,
    }


def see_automation_batch(request):
    # print(request.matchdict)
    # {'automation_slug': 'xxx', 'batch_slug': 'a'}
    # TODO: match batch name
    display_configuration = configuration['display']
    display_layout = display_configuration['layout'].casefold()
    if display_layout == 'input':
        # TODO
        pass
    elif display_layout == 'output':
        # template_markdown = ' '.join(
        # '{' + _ + '}' for _ in input_variable_ids)
        print(configuration['output'])
        template_path = join(
            configuration_folder,
            configuration['output']['templates'][0]['path'])
        template_markdown = open(template_path, 'rt').read()
        y_markdown = VARIABLE_ID_PATTERN.sub(
            render_variable_from_regex_match, template_markdown)
        # TODO: Think of a better name for y_markdown
        body = markdown(y_markdown)
    else:
        # TODO
        pass
    return {'body': body}


def see_automation_batch_file(request):
    print('see_automation_batch_file')
    # print(request.matchdict)
    from pyramid.response import FileResponse
    # here = os.path.dirname(__file__)
    # icon = os.path.join(here, "static", "favicon.ico")
    # return FileResponse(icon, request=request)
    # return Response('Automation Batch File')
    matchdict = request.matchdict
    # TODO: Screen variable path
    variable_path = matchdict['variable_path']
    path = join(configuration_folder, output_folder, variable_path)
    print(path)
    return FileResponse(path, request=request)


with Configurator() as config:
    config.include('pyramid_jinja2')
    # TODO: Build route urls progressively
    config.add_route('home', '/')
    config.add_route('automation', '/a/{automation_slug}')
    config.add_route('automation batch', '/a/{automation_slug}/b/{batch_slug}')
    config.add_route(
        'automation batch file',
        '/a/{automation_slug}/b/{batch_slug}/{variable_type}/{variable_path}')
    config.add_view(
        home,
        route_name='home',
        renderer='home.jinja2')
    config.add_view(
        see_automation_batch,
        route_name='automation batch',
        # renderer='automation-batch.jinja2',
        renderer='base.jinja2')
    config.add_view(
        see_automation_batch_file,
        route_name='automation batch file')
    app = config.make_wsgi_app()


# Start server
server = make_server('0.0.0.0', 8000, app)
server.serve_forever()

import webbrowser
from collections import OrderedDict
from configparser import RawConfigParser
from invisibleroads.scripts import Script
from invisibleroads_macros.disk import compress_zip, make_enumerated_folder
from os.path import basename, dirname, isabs, join
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest, HTTPSeeOther
from pyramid.response import FileResponse
from wsgiref.simple_server import make_server

from ..configurations import RESERVED_ARGUMENT_NAMES
from ..types import (
    get_data_type, get_data_type_packs, prepare_result_arguments)
from . import load_tool_definition, run_script


class ServeScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        tool_name = tool_definition['tool_name']
        app = get_app(
            tool_definition,
            base_template='base.jinja2',
            data_type_packs=get_data_type_packs(),
            data_folder=join('/tmp', tool_name))
        webbrowser.open_new_tab('http://127.0.0.1:4444/tools/0')
        server = make_server('127.0.0.1', 4444, app)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def get_app(tool_definition, base_template, data_type_packs, data_folder):
    config = Configurator(settings={
        'data.folder': data_folder,
        'data_type_packs': data_type_packs,
        'jinja2.directories': 'crosscompute:templates',
        'jinja2.lstrip_blocks': True,
        'jinja2.trim_blocks': True,
        'tool_definition': tool_definition,
        'website.name': 'CrossCompute',
        'website.root_asset_paths': [
            'invisibleroads_posts:assets/favicon.ico',
        ],
    })
    config.include('invisibleroads_posts')
    config.get_jinja2_environment().globals.update(get_template_variables(
        config.registry.settings, base_template))
    add_routes(config)
    return config.make_wsgi_app()


def get_template_variables(settings, base_template, tool_definition=None):
    tool_definition = tool_definition or settings['tool_definition']
    get_data_type_for = lambda x: get_data_type(x, settings['data_type_packs'])

    def format_value(value_key):
        if value_key + '.value' not in tool_definition:
            return ''
        value = tool_definition[value_key + '.value']
        data_type = get_data_type_for(value_key)
        if isinstance(value, basestring):
            value = data_type.parse(value)
        return data_type.format(value)

    def load_value(value_key, path):
        if not isabs(path):
            path = join(dirname(tool_definition['configuration_path']), path)
        return get_data_type_for(value_key).load(path)

    def prepare_tool_argument_noun(path_key):
        tool_argument_noun = path_key[:-5]
        if path_key + '.value' in tool_definition:
            tool_definition[tool_argument_noun + '.value'] = load_value(
                tool_argument_noun, tool_definition[path_key + '.value'])
        return tool_argument_noun

    return dict(
        RESERVED_ARGUMENT_NAMES=RESERVED_ARGUMENT_NAMES,
        base_template=base_template,
        format_value=format_value,
        get_data_type_for=get_data_type_for,
        prepare_tool_argument_noun=prepare_tool_argument_noun,
        tool_argument_names=tool_definition['argument_names'],
        tool_name=tool_definition['tool_name'])


def add_routes(config):
    config.add_route('tool', 'tools/{id}')
    config.add_route('result.json', 'results/{id}.json')
    config.add_route('result', 'results/{id}')
    config.add_route('result_name.zip', 'results/{id}/{name}.zip')

    config.add_view(
        show_tool, renderer='tool.jinja2', request_method='GET',
        route_name='tool')
    config.add_view(
        run_tool, request_method='POST',
        route_name='tool')
    config.add_view(
        show_result, renderer='result.jinja2', request_method='GET',
        route_name='result')
    config.add_view(
        show_result_json, renderer='json', request_method='GET',
        route_name='result.json')
    config.add_view(
        show_result_zip, request_method='GET',
        route_name='result_name.zip')


def show_tool(request):
    # !! Render markdown
    return {}


def run_tool(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    data_type_packs = settings['data_type_packs']
    data_folder = settings['data.folder']
    try:
        result_arguments = prepare_result_arguments(
            tool_definition['argument_names'], request.params, data_type_packs,
            data_folder)
    except TypeError as e:
        raise HTTPBadRequest(dict(e.args))
    target_folder = make_enumerated_folder(join(data_folder, 'results'))
    run_script(
        target_folder, tool_definition, result_arguments, data_type_packs,
        save_logs=True)
    compress_zip(target_folder)
    result_id = basename(target_folder)
    return HTTPSeeOther(request.route_path('result', id=result_id))


def show_result(request):
    settings = request.registry.settings
    result_id = request.matchdict['id']
    target_folder = join(settings['data.folder'], 'results', result_id)
    result_configuration = RawConfigParser()
    result_configuration.read(join(target_folder, 'result.cfg'))
    result_arguments = OrderedDict(result_configuration['result_arguments'])
    result_properties = OrderedDict(result_configuration['result_properties'])
    return dict(
        result_id=result_id,
        result_arguments=result_arguments,
        result_properties=result_properties)


def show_result_json(request):
    pass


def show_result_zip(request):
    settings = request.registry.settings
    result_id = request.matchdict['id']
    target_folder = join(settings['data.folder'], 'results', result_id)
    result_archive_path = target_folder + '.zip'
    return FileResponse(result_archive_path, request=request)

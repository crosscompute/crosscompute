import webbrowser
from configparser import RawConfigParser
from invisibleroads.scripts import Script
from invisibleroads_macros.disk import compress_zip, make_enumerated_folder
from invisibleroads_macros.log import parse_nested_dictionary_from
from os.path import basename, dirname, isabs, join, sep
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest, HTTPSeeOther
from pyramid.response import FileResponse
from six import string_types
from wsgiref.simple_server import make_server

from ..configurations import RESERVED_ARGUMENT_NAMES
from ..types import (
    get_data_type, get_data_type_packs, get_result_arguments,
    parse_data_dictionary_from)
from . import load_tool_definition, run_script


HELP_BY_KEY = {
    'return_code': 'There was an error while running the script.',
    'standard_error': 'The script wrote data to the standard error stream.',
    'standard_output': 'The script wrote data to the standard output stream.',
}


class ServeScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        app = get_app(tool_definition, data_type_packs=get_data_type_packs())
        webbrowser.open_new_tab('http://127.0.0.1:4444/tools/1')
        server = make_server('127.0.0.1', 4444, app)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def get_app(
        tool_definition,
        base_template='invisibleroads_posts:templates/base.jinja2',
        data_type_packs=None, data_folder=None):
    tool_name = tool_definition['tool_name']
    config = Configurator(settings={
        'data.folder': data_folder or join(sep, 'tmp', tool_name),
        'data_type_packs': data_type_packs or [],
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
        if value_key not in tool_definition:
            return ''
        value = tool_definition[value_key]
        data_type = get_data_type_for(value_key)
        if isinstance(value, string_types):
            value = data_type.parse(value)
        return data_type.format(value)

    def load_value(value_key, path):
        if not isabs(path):
            path = join(dirname(tool_definition['configuration_path']), path)
        return get_data_type_for(value_key).load(path)

    def prepare_tool_argument_noun(path_key):
        tool_argument_noun = path_key[:-5]
        if path_key in tool_definition:
            tool_definition[tool_argument_noun] = load_value(
                tool_argument_noun, tool_definition[path_key])
        return tool_argument_noun

    return dict(
        RESERVED_ARGUMENT_NAMES=RESERVED_ARGUMENT_NAMES,
        base_template=base_template,
        data_folder=settings['data.folder'],
        format_value=format_value,
        get_data_type_for=get_data_type_for,
        get_help=lambda x: tool_definition.get(
            x + '.help', HELP_BY_KEY.get(x, '')),
        prepare_tool_argument_noun=prepare_tool_argument_noun,
        tool_argument_names=tool_definition['argument_names'],
        tool_name=tool_definition['tool_name'])


def add_routes(config):
    config.add_route('tool', 'tools/{id}')
    config.add_route('result.json', 'results/{id}.json')
    config.add_route('result', 'results/{id}')
    config.add_route('result_name.zip', 'results/{id}/{name}.zip')
    config.add_route('result_file', 'results/{id}/{name}')

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
    config.add_view(
        show_result_file, request_method='GET',
        route_name='result_file')


def show_tool(request):
    # !! Render markdown
    settings = request.registry.settings
    data_type_packs = settings['data_type_packs']
    return dict(
        data_types=zip(*data_type_packs)[1])

    [y() for y in set(x.__class__ for x in xs)]


get_unique_data_types


def run_tool(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    data_type_packs = settings['data_type_packs']
    data_folder = settings['data.folder']
    try:
        result_arguments = get_result_arguments(
            tool_definition, request.params, data_type_packs, data_folder)
    except TypeError as e:
        raise HTTPBadRequest(dict(e.args))
    target_folder = make_enumerated_folder(join(data_folder, 'results'))
    run_script(
        target_folder, tool_definition, result_arguments, data_type_packs)
    compress_zip(target_folder, excludes=[
        'standard_output.log', 'standard_error.log'])
    result_id = basename(target_folder)
    return HTTPSeeOther(request.route_path('result', id=result_id))


def show_result(request):
    settings = request.registry.settings
    configuration_folder = dirname(settings['tool_definition'][
        'configuration_path'])
    result_id = request.matchdict['id']
    target_folder = join(settings['data.folder'], 'results', result_id)
    result_configuration = RawConfigParser()
    result_configuration.read(join(target_folder, 'result.cfg'))
    data_type_packs = get_data_type_packs()
    parse_value_by_key = lambda d: parse_data_dictionary_from(
        d, data_type_packs, configuration_folder)[0]
    result_arguments = parse_value_by_key(
        result_configuration['result_arguments'])
    result_arguments.pop('target_folder')
    result_properties = parse_value_by_key(parse_nested_dictionary_from(
        result_configuration['result_properties'], max_depth=1))
    return dict(
        data_types=zip(*data_type_packs)[1],
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


def show_result_file(request):
    settings = request.registry.settings
    result_id = request.matchdict['id']
    target_folder = join(settings['data.folder'], 'results', result_id)
    result_file_name = basename(request.matchdict['name'])
    result_file_path = join(target_folder, result_file_name)
    return FileResponse(result_file_path, request=request)

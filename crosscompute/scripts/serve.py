import codecs
import re
import webbrowser
from collections import OrderedDict
from importlib import import_module
from invisibleroads.scripts import Script
from invisibleroads_macros.disk import (
    compress_zip, make_enumerated_folder, resolve_relative_path)
from invisibleroads_macros.iterable import merge_dictionaries
from invisibleroads_posts.exceptions import HTTPBadRequestJSON
from invisibleroads_posts.views import expect_param
from invisibleroads_uploads.views import get_upload_from
from markupsafe import Markup
from mistune import Markdown
from os import environ
from os.path import basename, exists, isabs, join, sep
from pyramid.config import Configurator
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPSeeOther)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from six import string_types
from traceback import format_exc
from wsgiref.simple_server import make_server

from ..configurations import ARGUMENT_NAME_PATTERN, RESERVED_ARGUMENT_NAMES
from ..exceptions import DataTypeError
from ..types import (
    DataItem, get_data_type, get_data_type_by_name, get_data_type_by_suffix,
    get_result_arguments)
from . import load_result_configuration, load_tool_definition, run_script


HELP = {
    'return_code': 'There was an error while running the script.',
    'standard_error': 'The script wrote to the standard error stream.',
    'standard_output': 'The script wrote to the standard output stream.',
}
MARKDOWN_TITLE_PATTERN = re.compile(r'^#[^#]\s*(.+)')


class ServeScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')
        argument_subparser.add_argument('--host', default='127.0.0.1')
        argument_subparser.add_argument('--port', default=4444, type=int)

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        app = get_app(
            tool_definition, data_type_by_suffix=get_data_type_by_suffix())
        app_url = 'http://%s:%s/tools/1' % (args.host, args.port)
        webbrowser.open_new_tab(app_url)
        server = make_server(args.host, args.port, app)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def get_app(
        tool_definition,
        base_template='invisibleroads_posts:templates/base.jinja2',
        data_type_by_suffix=None,
        data_folder=None):
    tool_name = tool_definition['tool_name']
    data_types = set(data_type_by_suffix.values())
    config = Configurator(settings={
        'data.folder': data_folder or join(sep, 'tmp', tool_name),
        'data_type_by_suffix': data_type_by_suffix or {},
        'jinja2.directories': 'crosscompute:templates',
        'jinja2.lstrip_blocks': True,
        'jinja2.trim_blocks': True,
        'tool_definition': tool_definition,
        'website.name': 'CrossCompute',
        'website.author': 'CrossCompute Inc',
        'website.root_assets': [
            'invisibleroads_posts:assets/favicon.ico',
        ],
        'website.style_assets': [
            'invisibleroads_posts:assets/part.min.css',
            'invisibleroads_uploads:assets/part.min.css',
        ] + [x.style for x in data_types if x.style],
        'website.script_assets': [
            'invisibleroads_posts:assets/part.min.js',
            'invisibleroads_uploads:assets/part.min.js',
        ] + [x.script for x in data_types if x.script],
    })
    config.include('invisibleroads_posts')
    config.include('invisibleroads_uploads')
    configure_jinja2_environment(config, base_template, r'results/(\d+)/(.+)')
    add_routes(config)
    add_routes_for_data_types(config)
    return config.make_wsgi_app()


def configure_jinja2_environment(
        config, base_template, result_path_expression, **kw):
    result_path_pattern = re.compile(result_path_expression)
    markdown = Markdown(escape=True, hard_wrap=True)

    def get_url_from_path(path):
        try:
            result_id, file_path = result_path_pattern.search(path).groups()
        except AttributeError:
            return ''
        return '/results/%s/_/%s' % (result_id, file_path)

    jinja2_environment = config.get_jinja2_environment()
    jinja2_environment.filters.update({
        'markdown': lambda x: Markup(markdown(x)),
    })
    jinja2_environment.globals.update({
        'base_template': base_template,
        'get_os_environment_variable': environ.get,
        'get_url_from_path': get_url_from_path,
    }, **kw)


def get_template_variables(tool_definition, template_type, data_items):
    template_path = get_template_path(tool_definition, template_type)
    if not template_path or not exists(template_path) or not data_items:
        title, parts = tool_definition['tool_name'], data_items
    else:
        template_text = codecs.open(template_path, 'r', 'utf-8').read()
        title, parts = parse_template(template_text, data_items)
    return {
        template_type + '_title': title,
        template_type + '_template_parts': parts,
    }


def get_template_path(tool_definition, template_type):
    template_relative_path = tool_definition.get(
        template_type + '_template_path', '')
    return join(
        tool_definition['configuration_folder'],
        template_relative_path) if template_relative_path else ''


def parse_template(template_text, data_items):
    title = MARKDOWN_TITLE_PATTERN.search(template_text).group(1)
    content = MARKDOWN_TITLE_PATTERN.sub('', template_text).strip()
    parts = []
    data_item_by_key = {x.key: x for x in data_items}
    for index, x in enumerate(ARGUMENT_NAME_PATTERN.split(content)):
        if not x.strip():
            continue
        if index % 2 == 1:
            try:
                x = data_item_by_key[x]
            except KeyError:
                x = '{ %s }' % x
        parts.append(x)
    return title, parts


def add_routes(config):
    config.add_route('tool', '/tools/{id}')
    config.add_route('result.json', '/results/{id}.json')
    config.add_route('result.zip', '/results/{id}/{name}.zip')
    config.add_route('result_file', '/results/{id}/_/{path:.+}')
    config.add_route('result', '/results/{id}')

    config.add_view(
        index,
        route_name='index')
    config.add_view(
        show_tool, renderer='tool.jinja2', request_method='GET',
        route_name='tool')
    config.add_view(
        run_tool, request_method='POST',
        route_name='tool')
    config.add_view(
        show_result_json, renderer='json', request_method='GET',
        route_name='result.json')
    config.add_view(
        show_result_zip, request_method='GET',
        route_name='result.zip')
    config.add_view(
        show_result_file, request_method='GET',
        route_name='result_file')
    config.add_view(
        show_result, renderer='result.jinja2', request_method='GET',
        route_name='result')


def add_routes_for_data_types(config):
    data_type_by_name = get_data_type_by_name()
    for data_type_name, data_type in data_type_by_name.items():
        root_module_name = data_type.__module__
        for relative_view_url in data_type.views:
            # Get route_url
            route_name = '%s/%s' % (data_type_name, relative_view_url)
            route_url = '/c/' + route_name
            # Get view
            view_url = root_module_name + '.' + relative_view_url
            module_url, view_name = view_url.rsplit('.', 1)
            module = import_module(module_url)
            view = getattr(module, view_name)
            # Add view
            config.add_route(route_name, route_url)
            config.add_view(view, permission='run_tool', route_name=route_name)


def index(request):
    return HTTPSeeOther(request.route_path('tool', id=1))


def show_tool(request):
    settings = request.registry.settings
    data_type_by_suffix = settings['data_type_by_suffix']
    tool_definition = settings['tool_definition']
    tool_arguments = get_tool_arguments(tool_definition)
    tool_items = get_data_items(
        tool_arguments, tool_definition, data_type_by_suffix)
    return merge_dictionaries(
        get_template_variables(tool_definition, 'tool', tool_items), {
            'data_types': set(x.data_type for x in tool_items),
            'tool_id': 1,
        })


def run_tool(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    data_type_by_suffix = settings['data_type_by_suffix']
    data_folder = settings['data.folder']
    try:
        result_arguments = get_result_arguments(
            tool_definition, request.params, data_type_by_suffix, data_folder,
            request.authenticated_userid)
    except DataTypeError as e:
        raise HTTPBadRequest(dict(e.args))
    target_folder = make_enumerated_folder(join(data_folder, 'results'))
    run_script(
        target_folder, tool_definition, result_arguments, data_type_by_suffix)
    compress_zip(target_folder, excludes=[
        'standard_output.log', 'standard_error.log'])
    return HTTPSeeOther(request.route_path(
        'result', id=basename(target_folder), _anchor='properties'))


def show_result(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    result_id = request.matchdict['id']

    result_arguments, result_properties = load_result_configuration(join(
        settings['data.folder'], 'results', result_id))
    data_type_by_suffix = get_data_type_by_suffix()
    tool_items = get_data_items(
        result_arguments, tool_definition, data_type_by_suffix)
    result_errors = get_data_items(merge_dictionaries(
            result_properties.pop('standard_errors', {}),
            result_properties.pop('type_errors', {})),
        tool_definition, data_type_by_suffix)
    result_items = get_data_items(
        result_properties.pop('standard_outputs', {}), tool_definition,
        data_type_by_suffix)
    result_properties = get_data_items(
        result_properties, tool_definition, data_type_by_suffix)
    return merge_dictionaries(
        get_template_variables(tool_definition, 'tool', tool_items),
        get_template_variables(tool_definition, 'result', result_items), {
            'data_types': set(x.data_type for x in tool_items + result_items),
            'tool_id': 1,
            'result_id': result_id,
            'result_errors': result_errors,
            'result_properties': result_properties,
        })


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
    try:
        result_file_path = resolve_relative_path(
            request.matchdict['path'], target_folder)
    except IOError:
        raise HTTPForbidden
    if not exists(result_file_path):
        raise HTTPNotFound
    return FileResponse(result_file_path, request=request)


def import_upload(request, DataType, render_property_kw):
    params = request.params
    upload = get_upload_from(request)
    name = expect_param('name', params)
    help_text = params.get('help', '')
    try:
        value = DataType.load(upload.path)
    except Exception as e:
        open(join(upload.folder, 'error.log'), 'wt').write(format_exc())
        if isinstance(e, DataTypeError):
            message = str(e)
        else:
            message = 'Import failed'
        raise HTTPBadRequestJSON({name: message})
    DataType.save(join(upload.folder, '%s.%s' % (
        DataType.suffixes[0], DataType.formats[0])), value)
    template = get_renderer(DataType.template).template_loader()
    data_item = DataItem(name, value, DataType, help_text)
    html = template.make_module().render_property(
        data_item, **render_property_kw)
    return Response(html)


def get_tool_arguments(tool_definition):
    value_by_key = OrderedDict()
    configuration_folder = tool_definition['configuration_folder']
    for key in tool_definition['argument_names']:
        value = tool_definition.get(key, '')
        if key.endswith('_path') and not isabs(value):
            value = join(configuration_folder, value)
        value_by_key[key] = value
    return value_by_key


def get_data_items(value_by_key, tool_definition, data_type_by_suffix):
    data_items = []
    for key, value in value_by_key.items():
        if key.startswith('_') or key in RESERVED_ARGUMENT_NAMES:
            continue
        if key.endswith('_path'):
            key = key[:-5]
            data_type = get_data_type(key, data_type_by_suffix)
            value = data_type.load_safely(value)
        else:
            data_type = get_data_type(key, data_type_by_suffix)
            if isinstance(value, string_types):
                value = data_type.parse(value)
        help_text = tool_definition.get(key + '.help', HELP.get(key, ''))
        data_items.append(DataItem(key, value, data_type, help_text))
    return data_items

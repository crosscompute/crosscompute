import codecs
import logging
import re
import webbrowser
from collections import OrderedDict
from invisibleroads_macros.disk import (
    compress_zip, copy_file, copy_text, get_file_extension, link_path,
    make_folder, make_unique_folder, move_path, remove_safely,
    resolve_relative_path)
from invisibleroads_macros.iterable import merge_dictionaries
from invisibleroads_posts import add_routes_for_fused_assets
from invisibleroads_posts.views import expect_param
from invisibleroads_uploads.views import get_upload, get_upload_from
from markupsafe import Markup
from mistune import markdown
from os import environ
from os.path import basename, exists, isabs, join
from pyramid.config import Configurator
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPSeeOther)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from six import string_types, text_type
from traceback import format_exc
from wsgiref.simple_server import make_server

from ..configurations import ARGUMENT_NAME_PATTERN
from ..exceptions import DataParseError, DataTypeError
from ..types import (
    DataItem, parse_data_dictionary_from, get_data_type, DATA_TYPE_BY_NAME,
    RESERVED_ARGUMENT_NAMES)
from . import (
    ToolScript, get_source_folder, get_target_folder,
    load_result_configuration, prepare_result_id, run_script,
    EXCLUDED_FILE_NAMES)


HELP = {
    'return_code': 'There was an error while running the script.',
    'standard_error': 'The script wrote to the standard error stream.',
    'standard_output': 'The script wrote to the standard output stream.',
}
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())
MARKDOWN_TITLE_PATTERN = re.compile(r'^#[^#]\s*(.+)')
RESULT_PATH_PATTERN = re.compile(r'results/(\w+)/([xy])/(.+)')
WEBSITE = {
    'name': 'CrossCompute',
    'owner': 'CrossCompute Inc',
    'url': 'https://crosscompute.com',
}


class ServeScript(ToolScript):

    def configure(self, argument_subparser):
        super(ServeScript, self).configure(argument_subparser)
        argument_subparser.add_argument(
            '--host', default='127.0.0.1')
        argument_subparser.add_argument(
            '--port', default=4444, type=int)
        argument_subparser.add_argument(
            '--website_name', default=WEBSITE['name'])
        argument_subparser.add_argument(
            '--website_owner', default=WEBSITE['owner'])
        argument_subparser.add_argument(
            '--website_url', default=WEBSITE['url'])

    def run(self, args):
        tool_definition, data_folder = super(ServeScript, self).run(args)
        app = get_app(
            tool_definition, data_folder, args.website_name,
            args.website_owner, args.website_url)
        app_url = 'http://%s:%s/t/1' % (args.host, args.port)
        webbrowser.open_new_tab(app_url)
        server = make_server(args.host, args.port, app)
        print('Running on http://%s:%s' % (args.host, args.port))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


class ResultRequest(object):

    reserved_argument_names = RESERVED_ARGUMENT_NAMES

    def __init__(self, request, tool_definition):
        self.request = request
        self.tool_definition = tool_definition

        settings = request.registry.settings
        self.data_folder = data_folder = settings['data.folder']

        params = request.params
        draft_folder = make_unique_folder(join(
            data_folder, 'drafts', 'results'))
        try:
            result_arguments = self.prepare_arguments(params, draft_folder)
        except DataParseError as e:
            raise HTTPBadRequest(e.message_by_name)
        self.result_id = result_id = self.prepare_result()
        self.result_arguments = self.migrate_arguments(
            result_arguments, get_source_folder(data_folder, result_id))
        self.target_folder = get_target_folder(data_folder, result_id)
        remove_safely(draft_folder)

    def prepare_arguments(self, raw_arguments, draft_folder):
        arguments, errors = OrderedDict(), OrderedDict()
        configuration_folder = self.tool_definition['configuration_folder']
        for argument_name in self.tool_definition['argument_names']:
            if argument_name in self.reserved_argument_names:
                continue
            if argument_name.endswith('_path'):
                argument_noun = argument_name[:-5]
                default_path = join(
                    configuration_folder, self.tool_definition[argument_name],
                ) if argument_name in self.tool_definition else None
                try:
                    v = self.prepare_argument_path(
                        argument_noun, raw_arguments, draft_folder,
                        default_path)
                except (IOError, ValueError):
                    errors[argument_noun] = 'invalid'
                    continue
                except KeyError:
                    errors[argument_noun] = 'required'
                    continue
            elif argument_name in raw_arguments:
                v = raw_arguments[argument_name].strip()
            else:
                errors[argument_name] = 'required'
                continue
            arguments[argument_name] = v
        if errors:
            raise DataParseError(errors, arguments)
        # Parse strings and validate data types
        return parse_data_dictionary_from(arguments, configuration_folder)

    def prepare_result(self):
        return prepare_result_id(self.data_folder)

    def migrate_arguments(self, result_arguments, source_folder):
        d = {}
        make_folder(source_folder)
        for k, v in result_arguments.items():
            if k.endswith('_path'):
                v = move_path(source_folder, basename(v), v)
            d[k] = v
        return d

    def prepare_argument_path(
            self, argument_noun, raw_arguments, draft_folder, default_path):
        data_type = get_data_type(argument_noun)
        # If client sent direct content (x_table_csv), save it
        for file_format in data_type.formats:
            raw_argument_name = '%s_%s' % (argument_noun, file_format)
            if raw_argument_name not in raw_arguments:
                continue
            return copy_text(draft_folder, '%s.%s' % (
                argument_noun, file_format), raw_arguments[raw_argument_name])
        # Raise KeyError if client did not specify noun (x_table)
        v = raw_arguments[argument_noun]
        # If client sent multipart content, save it
        if hasattr(v, 'file'):
            return copy_file(draft_folder, argument_noun + get_file_extension(
                v.filename), v.file)
        # If client sent empty content, use default
        if v == '':
            if not default_path:
                raise KeyError
            return link_path(draft_folder, argument_noun + get_file_extension(
                default_path), default_path)
        # If client sent a relative path (x_table=11/x/y.csv), find it
        if '/' in v:
            source_path = self.get_file_path(*parse_result_relative_path(v))
            return link_path(draft_folder, argument_noun + get_file_extension(
                source_path), source_path)
        # If client sent an upload id (x_table=x), find it
        upload = get_upload(self.request, upload_id=v)
        source_path = join(upload.folder, data_type.get_file_name())
        return link_path(draft_folder, argument_noun + get_file_extension(
            source_path), source_path)

    def get_file_path(self, result_id, folder_name, path):
        result_folder = join(self.data_folder, 'results', result_id)
        parent_folder = join(result_folder, folder_name)
        return resolve_relative_path(path, parent_folder)


def get_app(
        tool_definition, data_folder, website_name=None, website_owner=None,
        website_url=None):
    settings = {
        'data.folder': data_folder,
        'website.name': website_name or WEBSITE['name'],
        'website.owner': website_owner or WEBSITE['owner'],
        'website.url': website_url or WEBSITE['url'],
        'website.root_assets': [
            'invisibleroads_posts:assets/favicon.ico',
            'invisibleroads_posts:assets/robots.txt',
        ],
        'jinja2.directories': 'crosscompute:templates',
        'jinja2.lstrip_blocks': True,
        'jinja2.trim_blocks': True,
    }
    settings['tool_definition'] = tool_definition
    config = Configurator(settings=settings)
    config.include('invisibleroads_posts')
    includeme(config)
    add_routes(config)
    add_routes_for_fused_assets(config)
    return config.make_wsgi_app()


def includeme(config):
    config.include('invisibleroads_uploads')
    configure_settings(config)
    configure_jinja2_environment(config)
    add_routes_for_data_types(config)


def configure_settings(config):
    settings = config.registry.settings
    settings['website.dependencies'].append(config.package_name)


def configure_jinja2_environment(config):
    settings = config.registry.settings
    jinja2_environment = config.get_jinja2_environment()
    jinja2_environment.filters.update({
        'markdown': lambda x: Markup(markdown(x, escape=True, hard_wrap=True)),
    })
    jinja2_environment.globals.update({
        'item_template': settings.get(
            'crosscompute.item_template',
            'crosscompute:templates/item.jinja2'),
        'get_os_environment_variable': environ.get,
    })


def add_routes_for_data_types(config):
    settings = config.registry.settings
    website_dependencies = settings['website.dependencies']
    for data_type_name, data_type in DATA_TYPE_BY_NAME.items():
        module_name = data_type.__module__
        for relative_view_url in data_type.views:
            # Get route_url
            route_name = '%s/%s' % (data_type_name, relative_view_url)
            route_url = '/c/' + route_name
            # Get view
            view = config.maybe_dotted(module_name + '.' + relative_view_url)
            # Add view
            config.add_route(route_name, route_url)
            config.add_view(view, permission='run_tool', route_name=route_name)
        website_dependencies.append(module_name)


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
    config.add_route('tool.json', '/t/{tool_id}.json')
    config.add_route('tool', '/t/{tool_id}')
    config.add_route('result.json', '/r/{result_id}.json')
    config.add_route('result.zip', '/r/{result_id}/{result_name}.zip')
    config.add_route('result_file', '/r/{result_id}/{folder_name}/{path:.+}')
    config.add_route('result', '/r/{result_id}')

    config.add_view(
        index,
        route_name='index')
    config.add_view(
        see_tool, renderer='tool.jinja2', request_method='GET',
        route_name='tool')
    config.add_view(
        run_tool_json, renderer='json', request_method='POST',
        route_name='tool.json')
    """
    config.add_view(
        see_result_json, renderer='json', request_method='GET',
        route_name='result.json')
    """
    config.add_view(
        see_result_zip, request_method='GET',
        route_name='result.zip')
    config.add_view(
        see_result_file, request_method='GET',
        route_name='result_file')
    config.add_view(
        see_result, renderer='result.jinja2', request_method='GET',
        route_name='result')


def index(request):
    return HTTPSeeOther(request.route_path('tool', tool_id=1))


def see_tool(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    return get_tool_template_variables(tool_definition, tool_id=1)


def run_tool_json(request):
    settings = request.registry.settings
    tool_definition = settings['tool_definition']
    r = ResultRequest(request, tool_definition)
    run_script(r.target_folder, tool_definition, r.result_arguments)
    compress_zip(r.target_folder, excludes=EXCLUDED_FILE_NAMES)
    return {
        'result_id': r.result_id,
        'result_url': request.route_path(
            'result', result_id=r.result_id, _anchor='properties'),
    }


def see_result(request):
    settings = request.registry.settings
    data_folder = settings['data.folder']
    tool_definition = settings['tool_definition']
    result_id = basename(request.matchdict['result_id'])
    target_folder = get_target_folder(data_folder, result_id)
    if not exists(target_folder):
        raise HTTPNotFound
    result_arguments, result_properties = load_result_configuration(
        target_folder)
    tool_items = get_data_items(result_arguments, tool_definition)
    result_errors = get_data_items(merge_dictionaries(
        result_properties.pop('standard_errors', {}),
        result_properties.pop('type_errors', {}),
    ), tool_definition)
    result_items = get_data_items(
        result_properties.pop('standard_outputs', {}), tool_definition)
    result_properties = get_data_items(
        result_properties, tool_definition)
    return merge_dictionaries(
        get_template_variables(tool_definition, 'tool', tool_items),
        get_template_variables(tool_definition, 'result', result_items), {
            'data_types': set(x.data_type for x in tool_items + result_items),
            'tool_id': 1,
            'result_id': result_id,
            'result_errors': result_errors,
            'result_properties': result_properties,
        })


"""
def see_result_json(request):
    pass
"""


def see_result_zip(request):
    settings = request.registry.settings
    data_folder = settings['data.folder']
    result_id = request.matchdict['result_id']
    result_archive_path = get_target_folder(data_folder, result_id) + '.zip'
    return FileResponse(result_archive_path, request=request)


def see_result_file(request):
    matchdict = request.matchdict
    folder_name = matchdict['folder_name']
    if folder_name not in ('x', 'y'):
        raise HTTPForbidden
    settings = request.registry.settings
    data_folder = settings['data.folder']
    result_id = matchdict['result_id']
    parent_folder = join(data_folder, 'results', result_id, folder_name)
    try:
        file_path = resolve_relative_path(matchdict['path'], parent_folder)
    except IOError:
        raise HTTPForbidden
    if basename(file_path) in EXCLUDED_FILE_NAMES:
        raise HTTPForbidden
    if not exists(file_path):
        raise HTTPNotFound
    return FileResponse(file_path, request=request)


def import_upload(request, DataType, render_property_kw):
    params = request.params
    upload = get_upload_from(request)
    name = expect_param('argument_name', params)
    help_text = params.get('help', '')
    try:
        value = DataType.load(upload.path)
    except Exception as e:
        traceback_text = format_exc()
        codecs.open(join(
            upload.folder, 'error.log'), 'w', encoding='utf-8',
        ).write(traceback_text)
        if isinstance(e, DataTypeError):
            message = text_type(e)
        else:
            LOG.error(traceback_text)
            message = 'Import failed'
        raise HTTPBadRequest({name: message})
    DataType.save(join(upload.folder, DataType.get_file_name()), value)
    template = get_renderer(DataType.template).template_loader()
    data_item = DataItem(name, value, DataType, help_text)
    html = template.make_module().render_property(
        data_item, **render_property_kw)
    return Response(html)


def get_tool_template_variables(tool_definition, tool_id):
    tool_arguments = get_tool_arguments(tool_definition)
    tool_items = get_data_items(tool_arguments, tool_definition)
    return merge_dictionaries(
        get_template_variables(tool_definition, 'tool', tool_items), {
            'data_types': set(x.data_type for x in tool_items),
            'tool_id': tool_id,
        })


def get_tool_arguments(tool_definition):
    value_by_key = OrderedDict()
    configuration_folder = tool_definition['configuration_folder']
    for key in tool_definition['argument_names']:
        value = tool_definition.get(key, '')
        if key.endswith('_path') and not isabs(value):
            value = join(configuration_folder, value)
        value_by_key[key] = value
    return value_by_key


def get_data_items(value_by_key, tool_definition):
    data_items = []
    for key, value in value_by_key.items():
        if key.startswith('_') or key in RESERVED_ARGUMENT_NAMES:
            continue
        if key.endswith('_path'):
            key = key[:-5]
            data_type = get_data_type(key)
            file_location = get_file_location(value)
            value = data_type.load_safely(value)
        else:
            data_type = get_data_type(key)
            if isinstance(value, string_types):
                value = data_type.parse(value)
            file_location = ''
        help_text = tool_definition.get(key + '.help', HELP.get(key, ''))
        data_items.append(DataItem(
            key, value, data_type, file_location, help_text))
    return data_items


def get_file_url(result_path):
    try:
        result_id, folder_name, path = RESULT_PATH_PATTERN.search(
            result_path).groups()
    except AttributeError:
        return ''
    return '/r/%s/%s/%s' % (result_id, folder_name, path)


def get_file_location(result_path):
    try:
        result_id, folder_name, path = RESULT_PATH_PATTERN.search(
            result_path).groups()
    except AttributeError:
        return ''
    return '%s/%s/%s' % (result_id, folder_name, path)


def parse_result_relative_path(result_relative_path):
    result_id, folder_name, path = result_relative_path.split('/', 2)
    if folder_name not in ('x', 'y'):
        raise ValueError
    return result_id, folder_name, path

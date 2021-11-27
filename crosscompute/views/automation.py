# TODO: List links for all automations
# TODO: Let user set automation slug in configuration file
# TODO: Let user set batch name and slug
# TODO: Let user customize homepage title
# TODO: Add tests
# TODO: Validate variable definitions for id and view


import json
import logging
from abc import ABC, abstractmethod
from markdown import markdown
from os import getenv
from os.path import basename, exists, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse
from string import Template

from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    HOME_ROUTE,
    PAGE_ROUTE,
    PAGE_TYPE_NAME_BY_LETTER,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN)
from ..macros import (
    extend_uniquely,
    find_item,
    get_slug_from_name,
    is_path_in_folder)


MAP_MAPBOX_STYLE_URI = 'mapbox://styles/mapbox/dark-v10'
MAP_MAPBOX_SCRIPT_TEXT_TEMPLATE = Template('''\
const $element_id = new mapboxgl.Map({
    container: '$element_id',
    style: '$style_uri',
    center: $center_coordinates,
    zoom: $zoom_level,
})
$element_id.on('load', () => {
    $element_id.addSource('$element_id', {
        'type': 'geojson',
        'data': '$data_uri'})
    $element_id.addLayer({
        'id': '$element_id',
        'type': 'fill',
        'source': '$element_id'})
})''')


class AutomationViews():

    def __init__(self, configuration, configuration_folder):
        self.configuration = configuration
        self.configuration_folder = configuration_folder
        # TODO: Consider moving rest to a separate function
        automation_definitions = []
        automation_name = configuration.get(
            'name', AUTOMATION_NAME.format(automation_index=0))
        automation_slug = get_slug_from_name(automation_name)
        automation_uri = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)

        batch_definitions = []
        for batch_definition in configuration.get('batches', []):
            try:
                batch_folder = batch_definition['folder']
            except KeyError:
                logging.error('folder required for each batch')
                continue
            batch_name = batch_definition.get('name', basename(batch_folder))
            batch_slug = get_slug_from_name(batch_name)
            batch_uri = BATCH_ROUTE.format(batch_slug=batch_slug)
            batch_definitions.append({
                'name': batch_name,
                'slug': batch_slug,
                'uri': batch_uri,
                'folder': batch_folder,
            })

        automation_definitions.append({
            'name': automation_name,
            'slug': automation_slug,
            'uri': automation_uri,
            'batches': batch_definitions,
        })
        self.automation_definitions = automation_definitions
        self.css_uris = self.get_css_uris()

    def includeme(self, config):
        config.include(self.configure_styles)

        config.add_route('home', HOME_ROUTE)
        config.add_route('automation', AUTOMATION_ROUTE)
        config.add_route('automation batch', AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch page',
            AUTOMATION_ROUTE + BATCH_ROUTE + PAGE_ROUTE)
        config.add_route(
            'automation batch page file',
            AUTOMATION_ROUTE + BATCH_ROUTE + PAGE_ROUTE + FILE_ROUTE)

        config.add_view(
            self.see_home,
            route_name='home',
            renderer='crosscompute:templates/home.jinja2')
        config.add_view(
            self.see_automation,
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')
        config.add_view(
            self.see_automation_batch,
            route_name='automation batch',
            renderer='crosscompute:templates/batch.jinja2')
        config.add_view(
            self.see_automation_batch_page,
            route_name='automation batch page',
            renderer='crosscompute:templates/live.jinja2')
        config.add_view(
            self.see_automation_batch_page_file,
            route_name='automation batch page file')

    def configure_styles(self, config):
        if self.css_uris:
            config.add_route('style', STYLE_ROUTE)
            config.add_view(
                self.see_style,
                route_name='style')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'css_uris': self.css_uris,
                'HOME_ROUTE': HOME_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_style(self, request):
        if request.path not in self.css_uris:
            raise HTTPNotFound

        matchdict = request.matchdict
        style_path = matchdict['style_path']
        folder = self.configuration_folder
        path = join(folder, style_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest

        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def see_home(self, request):
        return {
            'automations': self.automation_definitions,
        }

    def see_automation(self, request):
        return self.get_automation_definition_from(request)

    def see_automation_batch(self, request):
        return {}

    def see_automation_batch_page(self, request):
        page_type_name = self.get_page_type_name_from(request)
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        batch_folder = batch_definition['folder']
        variable_folder = join(batch_folder, page_type_name)
        folder = join(self.configuration_folder, variable_folder)
        variable_definitions = self.get_variable_definitions(
            page_type_name)
        template_texts = self.get_template_texts(page_type_name)
        page_text = '\n'.join(template_texts)
        return render_page_dictionary(
            request, self.css_uris, page_type_name, page_text,
            variable_definitions, folder)

    def see_automation_batch_page_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        page_type_name = self.get_page_type_name_from(request)
        variable_definitions = self.get_variable_definitions(
            page_type_name)
        variable_path = matchdict['variable_path']
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        logging.debug(variable_definition)
        batch_folder = batch_definition['folder']
        variable_folder = join(batch_folder, page_type_name)
        folder = join(self.configuration_folder, variable_folder)
        path = join(folder, variable_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest
        return FileResponse(path, request=request)

    def get_automation_definition_from(self, request):
        matchdict = request.matchdict
        automation_slug = matchdict['automation_slug']
        try:
            automation_definition = find_item(
                self.automation_definitions, 'slug', automation_slug,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        return automation_definition

    def get_batch_definition_from(self, request, automation_definition):
        matchdict = request.matchdict
        batch_slug = matchdict['batch_slug']
        try:
            batch_definition = find_item(
                automation_definition['batches'], 'slug',
                batch_slug, normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        return batch_definition

    def get_page_type_name_from(self, request):
        matchdict = request.matchdict
        page_type_letter = matchdict['page_type']
        try:
            page_type_name = PAGE_TYPE_NAME_BY_LETTER[
                page_type_letter]
        except KeyError:
            raise HTTPBadRequest
        return page_type_name

    def get_css_uris(self):
        display_configuration = self.configuration.get('display', {})
        css_uris = []

        for style_definition in display_configuration.get('styles', []):
            uri = style_definition.get('uri', '').strip()
            path = style_definition.get('path', '').strip()
            if not uri and not path:
                logging.error('uri or path required for each style')
                continue
            if path:
                if not exists(join(self.configuration_folder, path)):
                    logging.error('style not found at path %s', path)
                uri = STYLE_ROUTE.format(style_path=path)
            css_uris.append(uri)

        return css_uris

    def get_variable_definitions(self, variable_type_name):
        return self.configuration.get(
            variable_type_name, {}).get('variables', [])

    def get_template_definitions(self, variable_type_name):
        return self.configuration.get(
            variable_type_name, {}).get('templates', [])

    def get_template_texts(self, variable_type_name):
        template_definitions = self.get_template_definitions(
            variable_type_name)
        template_paths = [
            _['path'] for _ in template_definitions if 'path' in _]
        if template_paths:
            template_texts = [open(join(
                self.configuration_folder, _,
            ), 'rt').read() for _ in template_paths]
        else:
            variable_definitions = self.get_variable_definitions(
                variable_type_name)
            variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
            template_texts = [' '.join('{' + _ + '}' for _ in variable_ids)]
        return template_texts


class VariableView(ABC):

    @abstractmethod
    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        return {
            'css_uris': [],
            'js_uris': [],
            'html_text': '',
            'js_texts': [],
        }


class NullView(VariableView):

    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        return {
            'css_uris': [],
            'js_uris': [],
            'html_text': '',
            'js_texts': [],
        }


class NumberView(VariableView):

    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        element_id = f'v{variable_index}'
        html_text = (
            f'<input id="{element_id}" '
            f'class="{type_name} number {variable_id}" '
            f'value="{variable_data}" type="number">')
        return {
            'css_uris': [],
            'js_uris': [],
            'html_text': html_text,
            'js_texts': [],
        }


class ImageView(VariableView):

    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        # TODO: Support type_name == 'input'
        element_id = f'v{variable_index}'
        data_uri = request_path + '/' + variable_path
        html_text = (
            f'<img id="{element_id}" '
            f'class="{type_name} image {variable_id}" '
            f'src="{data_uri}">'
        )
        return {
            'css_uris': [],
            'js_uris': [],
            'html_text': html_text,
            'js_texts': [],
        }


class MapMapboxView(VariableView):

    css_uri = 'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.css'
    js_uri = 'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.js'

    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        element_id = f'v{variable_index}'
        html_text = (
            f'<div id="{element_id}" '
            f'class="{type_name} map-mapbox {variable_id}"></div>')
        data_uri = request_path + '/' + variable_path

        mapbox_token = getenv('MAPBOX_TOKEN')
        if not mapbox_token:
            logging.error('MAPBOX_TOKEN is not defined in the environment')
        style_uri = variable_settings.get('style', MAP_MAPBOX_STYLE_URI)

        js_texts = [
            f"mapboxgl.accessToken = '{mapbox_token}'",
            MAP_MAPBOX_SCRIPT_TEXT_TEMPLATE.substitute({
                'element_id': element_id,
                'data_uri': data_uri,
                'style_uri': style_uri,
                'center_coordinates': variable_settings.get('center', [0, 0]),
                'zoom_level': variable_settings.get('zoom', 0),
            }),
        ]
        # TODO: Allow specification of preserveDrawingBuffer
        return {
            'css_uris': [self.css_uri],
            'js_uris': [self.js_uri],
            'html_text': html_text,
            'js_texts': js_texts,
        }


class MapPyDeckScreenGridLayer(VariableView):

    def render(
            self, type_name, variable_index, variable_id, variable_data=None,
            variable_path=None, variable_settings=None, request_path=None):
        return {}


def render_page_dictionary(
        request, css_uris, page_type_name, page_text, variable_definitions,
        folder):
    css_uris = css_uris.copy()
    js_uris, js_texts, variable_ids = [], [], []

    def render_html(match):
        matching_text = match.group(0)
        variable_id = match.group(1)
        try:
            definition = find_item(variable_definitions, 'id', variable_id)
        except StopIteration:
            logging.warning(
                '%s specified in template but missing in configuration',
                variable_id)
            return matching_text
        # TODO: Load data from batch folder
        variable_ids.append(variable_id)
        variable_index = len(variable_ids) - 1
        variable_view = get_variable_view_class(definition)()
        variable_path = definition.get('path', '')
        variable_data = definition.get('data', '')
        variable_settings = get_variable_settings(definition, folder)
        d = variable_view.render(
            page_type_name, variable_index, variable_id, variable_data,
            variable_path, variable_settings, request.path)
        extend_uniquely(css_uris, d['css_uris'])
        extend_uniquely(js_uris, d['js_uris'])
        extend_uniquely(js_texts, d['js_texts'])
        return d['html_text']

    html_text = markdown(VARIABLE_ID_PATTERN.sub(render_html, page_text))
    return {
        'css_uris': css_uris,
        'js_uris': js_uris,
        'html_text': html_text,
        'js_text': '\n'.join(js_texts),
    }


def get_variable_view_class(variable_definition):
    # TODO: Validate views early
    try:
        view_name = variable_definition['view']
    except KeyError:
        logging.error('view required for each variable')
        return NullView
    try:
        # TODO: Load using importlib.metadata
        VariableView = {
            'number': NumberView,
            'image': ImageView,
            'map-mapbox': MapMapboxView,
        }[view_name]
    except KeyError:
        logging.error(f'{view_name} view not installed')
        return NullView
    return VariableView


def get_variable_settings(variable_definition, folder):
    variable_settings = variable_definition.get('settings', {})
    settings_path = variable_settings.get('path')
    if settings_path:
        try:
            settings = json.load(open(join(folder, settings_path), 'rt'))
        except OSError:
            logging.error(f'{settings_path} not found')
        else:
            variable_settings.update(settings)
    return variable_settings

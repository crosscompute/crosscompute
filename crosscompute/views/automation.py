# TODO: Let user set automation slug in configuration file
# TODO: Let user set batch name and slug
# TODO: List links for all automations
# TODO: Let user customize homepage title
# TODO: Add tests
# TODO: Validate variable definitions for id and view
# TODO: Log error if automation requires view that is not installed


import logging
from abc import ABC, abstractmethod
from markdown import markdown
from os import getenv
from os.path import basename, exists, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    HOME_ROUTE,
    REPORT_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_TYPE_NAME_BY_LETTER)
from ..macros import (
    append_once,
    find_item,
    get_slug_from_name,
    is_path_in_folder)


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
        self.style_uris = self.get_style_uris()

    def includeme(self, config):
        config.include(self.configure_styles_and_scripts)

        config.add_route('home', HOME_ROUTE)
        config.add_route('automation', AUTOMATION_ROUTE)
        config.add_route('automation batch', AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch report',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE)
        config.add_route(
            'automation batch report file',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE + FILE_ROUTE)

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
            self.see_automation_batch_report,
            route_name='automation batch report',
            renderer='crosscompute:templates/live.jinja2')
        config.add_view(
            self.see_automation_batch_report_file,
            route_name='automation batch report file')

    def configure_styles_and_scripts(self, config):
        if self.style_uris:
            config.add_route('style', STYLE_ROUTE)
            config.add_view(
                self.see_style,
                route_name='style')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'style_uris': self.style_uris,
                'HOME_ROUTE': HOME_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_style(self, request):
        if request.path not in self.style_uris:
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

    def see_automation_batch_report(self, request):
        variable_type_name = self.get_variable_type_name_from(request)
        variable_definitions = self.get_variable_definitions(
            variable_type_name)
        template_texts = self.get_template_texts(variable_type_name)

        def render_variable_from(match):
            replacement_text = matching_text = match.group(0)
            variable_id = match.group(1)
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', variable_id)
            except StopIteration:
                logging.warning(
                    '%s specified in template but missing in configuration',
                    variable_id)
                return matching_text
            view_name = variable_definition['view']
            # TODO: Load variable data from batch folder
            variable_data = variable_definition.get('data', '')
            variable_path = variable_definition.get('path', '')
            request_path = request.path
            # variable_view = self.variable_view_by_name[view_name]
            # variable_view.render(type_name, variable_definition)

            if variable_type_name == 'input':
                if view_name == 'number':
                    variable_view = NumberView()
                    replacement_text = variable_view.render(
                        variable_type_name, variable_id, variable_data,
                        variable_path, request_path)
            elif variable_type_name == 'output':
                if view_name == 'image':
                    # TODO: Split into crosscompute-image
                    # image_uri = request.path + '/' + variable_path
                    # replacement_text = f'<img src="{image_uri}">'
                    variable_view = ImageView()
                    replacement_text = variable_view.render(
                        variable_type_name, variable_id, variable_data,
                        variable_path, request_path)
                elif view_name == 'map-mapbox':
                    variable_view = MapMapboxView()
                    replacement_text = variable_view.render(
                        variable_type_name, variable_id, variable_data,
                        variable_path, request_path)
            return replacement_text

        report_markdown = VARIABLE_ID_PATTERN.sub(
            render_variable_from, '\n'.join(template_texts))
        report_content = markdown(report_markdown)

        print(VariableView.__dict__)

        return {
            'style_uris': self.style_uris + VariableView.style_uris,
            'script_uris': VariableView.script_uris,
            'content_html': report_content,
            'script_text': '\n'.join(VariableView.script_texts),
        }

    def see_automation_batch_report_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        variable_type_name = self.get_variable_type_name_from(request)
        variable_definitions = self.get_variable_definitions(
            variable_type_name)
        variable_path = matchdict['variable_path']
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        logging.debug(variable_definition)
        batch_folder = batch_definition['folder']
        variable_folder = join(batch_folder, variable_type_name)
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

    def get_variable_type_name_from(self, request):
        matchdict = request.matchdict
        variable_type_letter = matchdict['variable_type']
        try:
            variable_type_name = VARIABLE_TYPE_NAME_BY_LETTER[
                variable_type_letter]
        except KeyError:
            raise HTTPBadRequest
        return variable_type_name

    def get_style_uris(self):
        display_configuration = self.configuration.get('display', {})
        style_uris = []

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
            style_uris.append(uri)

        return style_uris

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

    index = -1
    style_uris = []
    style_texts = []
    script_uris = []
    script_texts = []

    def __init__(self):
        if hasattr(self, 'initialize'):
            getattr(self, 'initialize')()
        VariableView.index += 1

    @abstractmethod
    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        pass


class NullView(VariableView):

    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        return ''


class NumberView(VariableView):

    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        return (
            f'<input type="number" class="{type_name} {variable_id}" '
            f'value="{variable_data}">')


class ImageView(VariableView):

    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        # TODO: Support type_name == 'input'
        image_uri = request_path + '/' + variable_path
        return f'<img class="{type_name} {variable_id}" src="{image_uri}">'


class MapMapboxView(VariableView):

    style_uri = 'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.css'
    script_uri = 'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.js'

    def initialize(self):
        append_once(MapMapboxView.style_uri, VariableView.style_uris)
        append_once(MapMapboxView.script_uri, VariableView.script_uris)
        mapbox_token = getenv('MAPBOX_TOKEN')
        if not mapbox_token:
            logging.error('MAPBOX_TOKEN is not defined in the environment')
        append_once(
            f"mapboxgl.accessToken = '{mapbox_token}'",
            VariableView.script_texts)

    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        element_id = f'v{VariableView.index}'
        # TODO: Allow override of style
        # TODO: Allow override of center
        # TODO: Allow override of zoom
        # TODO: Allow specification of preserveDrawingBuffer
        append_once((
            "new mapboxgl.Map({"
            f"container: '{element_id}',"
            "style: 'mapbox://styles/mapbox/streets-v11',"
            "center: [-74.5, 40],"
            "zoom: 5,"
            "preserveDrawingBuffer: true})"
        ), VariableView.script_texts)
        return (
            f'<div id="{element_id}" class="{type_name} {variable_id}">'
            '</div>')


'''
class MapPyDeckScreenGridView(VariableView):

    def render(
            self, type_name, variable_id, variable_data=None,
            variable_path=None, request_path=None):
        pass
'''

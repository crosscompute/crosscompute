# TODO: Let user customize homepage title
# TODO: Add tests
# TODO: Validate variable definitions for id and view
# TODO: Let creator override mapbox js


import json
from logging import getLogger
from os.path import join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    FUNCTION_BY_NAME,
    PAGE_ROUTE,
    PAGE_TYPE_NAME_BY_LETTER,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN)
from ..macros import (
    extend_uniquely,
    find_item,
    is_path_in_folder)
from ..routines.configuration import (
    apply_functions,
    get_all_variable_definitions,
    get_css_uris,
    get_raw_variable_definitions,
    get_template_texts,
    get_variable_view_class,
    load_data)
from ..routines.web import get_html_from_markdown


L = getLogger(__name__)


class AutomationViews():

    def __init__(self, automation_definitions):
        self.automation_definitions = automation_definitions

    def includeme(self, config):
        config.include(self.configure_styles)

        config.add_route('home', '/')
        config.add_route(
            'automation',
            AUTOMATION_ROUTE)
        config.add_route(
            'automation batch',
            AUTOMATION_ROUTE + BATCH_ROUTE)
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
            renderer='crosscompute:templates/page.jinja2')
        config.add_view(
            self.see_automation_batch_page_file,
            route_name='automation batch page file')

    def configure_styles(self, config):
        config.add_route(
            'style', STYLE_ROUTE)
        config.add_route(
            'automation style', AUTOMATION_ROUTE + STYLE_ROUTE)

        config.add_view(
            self.see_style,
            route_name='style')
        config.add_view(
            self.see_style,
            route_name='automation style')

    def see_style(self, request):
        matchdict = request.matchdict
        if 'automation_slug' in matchdict:
            automation_definition = self.get_automation_definition_from(
                request)
        else:
            automation_definition = self.automation_definitions[0]

        expected_paths = [_.split('?')[0] for _ in get_css_uris(
            automation_definition) if '//' not in _]
        if request.environ['PATH_INFO'] not in expected_paths:
            raise HTTPNotFound

        style_path = matchdict['style_path']
        folder = automation_definition['folder']
        path = join(folder, style_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest

        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def see_home(self, request):
        'Render home with list of available automations'
        try:
            automation_definition = self.automation_definitions[0]
        except IndexError:
            css_uris = []
        else:
            css_uris = get_css_uris(automation_definition)
        return {
            'automations': self.automation_definitions,
            'css_uris': css_uris,
        }

    def see_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        css_uris = get_css_uris(automation_definition)
        return automation_definition | {
            'css_uris': css_uris,
        }

    def see_automation_batch(self, request):
        return {}

    def see_automation_batch_page(self, request):
        page_type_name = self.get_page_type_name_from(request)
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        batch_folder = batch_definition['folder']
        folder = join(automation_folder, batch_folder)
        variable_definitions = get_all_variable_definitions(
            automation_definition, page_type_name)
        template_texts = get_template_texts(
            automation_definition, page_type_name)
        css_uris = get_css_uris(automation_definition)
        page_text = '\n'.join(template_texts)
        return {
            'automation_definition': automation_definition,
            'batch_definition': batch_definition,
            'uri': request.path,
            'page_type_name': page_type_name,
        } | render_page_dictionary(
            request, css_uris, page_type_name, page_text,
            variable_definitions, folder)

    def see_automation_batch_page_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        page_type_name = self.get_page_type_name_from(request)
        variable_definitions = get_raw_variable_definitions(
            automation_definition, page_type_name)
        variable_path = matchdict['variable_path']
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        L.debug(variable_definition)
        batch_folder = batch_definition['folder']
        variable_folder = join(batch_folder, page_type_name)
        folder = join(automation_folder, variable_folder)
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


def render_page_dictionary(
        request, css_uris, page_type_name, page_text, variable_definitions,
        folder):
    css_uris = css_uris.copy()
    js_uris, js_texts, variable_ids = [], [], []

    def render_html(match):
        matching_text = match.group(0)
        expression_text = match.group(1)
        expression_terms = expression_text.split('|')
        variable_id = expression_terms[0].strip()
        try:
            definition = find_item(variable_definitions, 'id', variable_id)
        except StopIteration:
            L.warning(
                '%s in template but missing in automation configuration',
                variable_id)
            return matching_text
        page_folder = join(folder, definition['type'])
        variable_ids.append(variable_id)
        variable_index = len(variable_ids) - 1
        variable_view = get_variable_view_class(definition)()
        variable_path = definition.get('path', '')
        variable_data = '' if variable_view.is_asynchronous else load_data(
            join(page_folder, variable_path), variable_id)
        variable_data = apply_functions(
            variable_data, expression_terms[1:], FUNCTION_BY_NAME)
        variable_configuration = get_variable_configuration(
            definition, page_folder)
        d = variable_view.render(
            page_type_name, variable_index, variable_id, variable_data,
            variable_path, variable_configuration, request.path)
        extend_uniquely(css_uris, d['css_uris'])
        extend_uniquely(js_uris, d['js_uris'])
        extend_uniquely(js_texts, d['js_texts'])
        return d['body_text']

    return {
        'css_uris': css_uris,
        'js_uris': js_uris,
        'body_text': get_html_from_markdown(VARIABLE_ID_PATTERN.sub(
            render_html, page_text)),
        'js_text': '\n'.join(js_texts),
    }


def get_variable_configuration(variable_definition, folder):
    variable_configuration = variable_definition.get('configuration', {})
    configuration_path = variable_configuration.get('path')
    if configuration_path:
        try:
            configuration = json.load(open(join(
                folder, configuration_path), 'rt'))
        except OSError:
            L.error('%s not found', configuration_path)
        else:
            variable_configuration.update(configuration)
    return variable_configuration

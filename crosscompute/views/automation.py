# TODO: Let user customize root title
# TODO: Add tests
# TODO: Validate variable definitions for id and view
# TODO: Let creator override mapbox js


import json
from logging import getLogger
from os.path import basename, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    FUNCTION_BY_NAME,
    ID_LENGTH,
    PAGE_ROUTE,
    PAGE_TYPE_NAME_BY_LETTER,
    RUN_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN)
from ..exceptions import CrossComputeDataError
from ..macros import (
    extend_uniquely,
    find_item,
    is_path_in_folder,
    make_unique_folder)
from ..routines.configuration import (
    apply_functions,
    get_all_variable_definitions,
    get_css_uris,
    get_raw_variable_definitions,
    get_template_texts,
    get_variable_configuration,
    get_variable_view_class,
    load_data,
    parse_data_by_id)
from ..routines.web import get_html_from_markdown


L = getLogger(__name__)


class AutomationViews():

    def __init__(self, automation_definitions, automation_queue):
        self.automation_definitions = automation_definitions
        self.automation_queue = automation_queue

    def includeme(self, config):
        config.include(self.configure_styles)

        config.add_route('root', '/')
        config.add_route(
            'automation.json',
            AUTOMATION_ROUTE + '.json')
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
        config.add_route(
            'automation run',
            AUTOMATION_ROUTE + RUN_ROUTE)
        config.add_route(
            'automation run page',
            AUTOMATION_ROUTE + RUN_ROUTE + PAGE_ROUTE)
        config.add_route(
            'automation run page file',
            AUTOMATION_ROUTE + RUN_ROUTE + PAGE_ROUTE + FILE_ROUTE)

        config.add_view(
            self.see_root,
            route_name='root',
            renderer='crosscompute:templates/root.jinja2')
        config.add_view(
            self.see_automation,
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')
        config.add_view(
            self.run_automation,
            route_name='automation.json',
            renderer='json')
        '''
        config.add_view(
            self.see_automation_batch,
            route_name='automation batch',
            renderer='crosscompute:templates/batch.jinja2')
        '''
        config.add_view(
            self.see_automation_page,
            route_name='automation batch page',
            renderer='crosscompute:templates/page.jinja2')
        config.add_view(
            self.see_automation_page_file,
            route_name='automation batch page file')
        '''
        config.add_view(
            self.see_automation_run,
            route_name='automation run',
            renderer='crosscompute:templates/run.jinja2')
        '''
        config.add_view(
            self.see_automation_page,
            route_name='automation run page',
            renderer='crosscompute:templates/page.jinja2')
        config.add_view(
            self.see_automation_page_file,
            route_name='automation run page file')

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
        elif not self.automation_definitions:
            raise HTTPNotFound
        else:
            automation_definition = self.automation_definitions[0]
        style_definitions = automation_definition.get('display', {}).get(
            'styles', [])

        try:
            style_definition = find_item(
                style_definitions, 'uri', request.environ['PATH_INFO'])
        except StopIteration:
            raise HTTPNotFound
        path = join(automation_definition['folder'], style_definition['path'])

        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def see_root(self, request):
        'Render root with list of available automations'
        for automation_definition in self.automation_definitions:
            if 'parent' not in automation_definition:
                css_uris = get_css_uris(automation_definition)
                break
        else:
            css_uris = []
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

    def run_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        variable_definitions = get_raw_variable_definitions(
            automation_definition, 'input')
        try:
            data_by_id = dict(request.params) or request.json_body
        except json.JSONDecodeError:
            data_by_id = {}
        try:
            data_by_id = parse_data_by_id(data_by_id, variable_definitions)
        except CrossComputeDataError as e:
            raise HTTPBadRequest(e)
        runs_folder = join(automation_definition['folder'], 'runs')
        folder = make_unique_folder(runs_folder, ID_LENGTH)
        run_id = basename(folder)
        self.automation_queue.put((automation_definition, {
            'folder': folder,
            'data_by_id': data_by_id,
        }))
        if 'runs' not in automation_definition:
            automation_definition['runs'] = []
        run_uri = RUN_ROUTE.format(run_slug=run_id)
        automation_definition['runs'].append({
            'name': run_id,
            'slug': run_id,
            'folder': folder,
            'uri': run_uri,
        })
        # TODO: Charge target page depending on definition
        return {'id': run_id}

    def see_automation_batch(self, request):
        return {}

    def see_automation_page(self, request):
        page_type_name = self.get_page_type_name_from(request)
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        page_definition = self.get_page_definition_from(
            request, automation_definition)
        page_folder = page_definition['folder']
        folder = join(automation_folder, page_folder)
        variable_definitions = get_all_variable_definitions(
            automation_definition, page_type_name)
        template_texts = get_template_texts(
            automation_definition, page_type_name)
        css_uris = get_css_uris(automation_definition)
        page_text = '\n'.join(template_texts)
        return {
            'automation_definition': automation_definition,
            'page_definition': page_definition,
            'uri': request.path,
            'page_type_name': page_type_name,
        } | render_page_dictionary(
            request, css_uris, page_text, variable_definitions, folder)

    def see_automation_page_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        page_definition = self.get_page_definition_from(
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
        page_folder = page_definition['folder']
        variable_folder = join(page_folder, page_type_name)
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

    def get_page_definition_from(self, request, automation_definition):
        matchdict = request.matchdict
        if 'run_slug' in matchdict:
            slug = matchdict['run_slug']
            key = 'runs'
        else:
            slug = matchdict['batch_slug']
            key = 'batches'
        try:
            page_definition = find_item(
                automation_definition[key], 'slug', slug)
        except StopIteration:
            raise HTTPNotFound
        return page_definition

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
        request, css_uris, page_text, variable_definitions, folder):
    css_uris, js_uris, js_texts, variable_index = css_uris.copy(), [], [], 0

    def render_html(match):
        matching_text = match.group(0)
        expression_terms = match.group(1).split('|')
        variable_id = expression_terms[0].strip()
        try:
            definition = find_item(variable_definitions, 'id', variable_id)
        except StopIteration:
            L.warning('%s in template but not in configuration', variable_id)
            return matching_text
        variable_view = get_variable_view_class(definition)()
        variable_path = definition['path']
        variable_type_name = definition['type']
        page_folder = join(folder, variable_type_name)
        variable_data = '' if variable_view.is_asynchronous else load_data(
            join(page_folder, variable_path), variable_id)
        variable_data = apply_functions(
            variable_data, expression_terms[1:], FUNCTION_BY_NAME)
        variable_configuration = get_variable_configuration(
            definition, page_folder)
        nonlocal variable_index
        d = variable_view.render(
            variable_type_name, f'v{variable_index}', variable_id,
            variable_data, variable_path, variable_configuration, request.path)
        variable_index += 1
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

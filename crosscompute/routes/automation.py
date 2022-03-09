# TODO: Show runs with command line option
# TODO: Add unit tests
import json
from functools import partial
from invisibleroads_macros_disk import make_random_folder
from itertools import count
from logging import getLogger
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse, Response
from time import time

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    ID_LENGTH,
    MODE_NAME_BY_CODE,
    MODE_ROUTE,
    MUTATION_ROUTE,
    RUN_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_ROUTE)
from ..exceptions import CrossComputeDataError
from ..macros.iterable import extend_uniquely, find_item
from ..macros.web import get_html_from_markdown
from ..routines.batch import DiskBatch
from ..routines.configuration import BatchDefinition, VariableDefinition
from ..routines.variable import (
    Element,
    VariableView,
    parse_data_by_id)


class AutomationRoutes():

    def __init__(
            self, configuration, automation_definitions, automation_queue):
        self.configuration = configuration
        self.automation_definitions = automation_definitions
        self.automation_queue = automation_queue

    def includeme(self, config):
        config.include(self.configure_root)
        config.include(self.configure_styles)
        config.include(self.configure_automations)
        config.include(self.configure_batches)
        config.include(self.configure_runs)

    def configure_root(self, config):
        configuration = self.configuration
        config.add_route('root', '/')

        config.add_view(
            self.see_root,
            request_method='GET',
            route_name='root',
            renderer=configuration.get_template_path('root'))

    def configure_styles(self, config):
        config.add_route(
            'style', STYLE_ROUTE)
        config.add_route(
            'automation style', AUTOMATION_ROUTE + STYLE_ROUTE)

        config.add_view(
            self.see_style,
            request_method='GET',
            route_name='style')
        config.add_view(
            self.see_style,
            request_method='GET',
            route_name='automation style')

    def configure_automations(self, config):
        config.add_route(
            'automation.json',
            AUTOMATION_ROUTE + '.json')
        config.add_route(
            'automation',
            AUTOMATION_ROUTE)

        config.add_view(
            self.run_automation,
            request_method='POST',
            route_name='automation.json',
            renderer='json')
        config.add_view(
            self.see_automation,
            request_method='GET',
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')

    def configure_batches(self, config):
        config.add_route(
            'automation batch',
            AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch mode',
            AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE)
        config.add_route(
            'automation batch mode variable',
            AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_mode,
            request_method='GET',
            route_name='automation batch mode',
            renderer='crosscompute:templates/mode.jinja2')
        config.add_view(
            self.see_automation_batch_mode_variable,
            request_method='GET',
            route_name='automation batch mode variable')

    def configure_runs(self, config):
        config.add_route(
            'automation run',
            AUTOMATION_ROUTE + RUN_ROUTE)
        config.add_route(
            'automation run mode',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE)
        config.add_route(
            'automation run mode variable',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_mode,
            request_method='GET',
            route_name='automation run mode',
            renderer='crosscompute:templates/mode.jinja2')
        config.add_view(
            self.see_automation_batch_mode_variable,
            request_method='GET',
            route_name='automation run mode variable')

    def see_root(self, request):
        'Render root with a list of available automations'
        css_uris = self.configuration.css_uris
        return {
            'title_text': self.configuration.get('name', 'Automations'),
            'automations': self.automation_definitions,
            'css_uris': css_uris,
            'mutation_uri': MUTATION_ROUTE.format(uri=''),
            'mutation_timestamp': time(),
        }

    def see_style(self, request):
        matchdict = request.matchdict
        if 'automation_slug' in matchdict:
            automation_definition = self.get_automation_definition_from(
                request)
        else:
            automation_definition = self.configuration
        style_definitions = automation_definition.style_definitions
        try:
            style_definition = find_item(
                style_definitions, 'uri', request.environ['PATH_INFO'])
        except StopIteration:
            raise HTTPNotFound
        path = automation_definition.folder / style_definition['path']
        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def run_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        variable_definitions = automation_definition.get_variable_definitions(
            'input')
        try:
            data_by_id = dict(request.params) or request.json_body
        except json.JSONDecodeError:
            data_by_id = {}
        try:
            data_by_id = parse_data_by_id(data_by_id, variable_definitions)
        except CrossComputeDataError as e:
            raise HTTPBadRequest(e)
        runs_folder = automation_definition.folder / 'runs'
        folder = make_random_folder(runs_folder, ID_LENGTH)
        batch_definition = BatchDefinition({
            'folder': folder,
        }, data_by_id=data_by_id, is_run=True)
        self.automation_queue.put((automation_definition, batch_definition))
        automation_definition.run_definitions.append(batch_definition)
        run_id = batch_definition.name
        # TODO: Change target page depending on definition
        return {'id': run_id}

    def see_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        css_uris = automation_definition.css_uris
        uri = automation_definition.uri
        return {
            'name': automation_definition.name,
            'uri': uri,
            'batches': automation_definition.batch_definitions,
            'runs': automation_definition.run_definitions,
            'title_text': automation_definition.name,
            'css_uris': css_uris,
            'mutation_uri': MUTATION_ROUTE.format(uri=uri),
            'mutation_timestamp': time(),
        }

    def see_automation_batch_mode(self, request):
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        batch = DiskBatch(automation_definition, batch_definition)
        base_uri = request.registry.settings['base_uri']
        mode_name = self.get_mode_name_from(request)
        uri = request.path
        for_print = 'p' in request.params
        return {
            'title_text': batch_definition.name,
            'automation_definition': automation_definition,
            'batch_definition': batch_definition,
            'uri': uri,
            'mode_name': mode_name,
            'mutation_uri': MUTATION_ROUTE.format(uri=uri),
            'mutation_timestamp': time(),
        } | render_mode_dictionary(batch, base_uri, mode_name, for_print)

    def see_automation_batch_mode_variable(self, request):
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        mode_name = self.get_mode_name_from(request)
        variable_definitions = automation_definition.get_variable_definitions(
            mode_name)
        matchdict = request.matchdict
        variable_id = matchdict['variable_id']
        if mode_name == 'debug' and variable_id == 'return_code':
            variable_definition = VariableDefinition({
                'id': 'return_code',
                'view': 'number',
                'path': 'variables.dictionary',
            }, mode_name='debug')
        else:
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', variable_id,
                    normalize=str.casefold)
            except StopIteration:
                raise HTTPNotFound
        batch = DiskBatch(automation_definition, batch_definition)
        variable_data = batch.get_data(variable_definition)
        if 'path' in variable_data:
            return FileResponse(variable_data['path'], request=request)
        if 'value' in variable_data:
            return Response(str(variable_data['value']))
        if 'error' in variable_data:
            raise HTTPNotFound
        raise HTTPBadRequest

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
        if 'batch_slug' in matchdict:
            slug = matchdict['batch_slug']
            key = 'batch_definitions'
        else:
            slug = matchdict['run_slug']
            key = 'run_definitions'
        batch_definitions = getattr(automation_definition, key)
        try:
            batch_definition = find_item(batch_definitions, 'slug', slug)
        except StopIteration:
            raise HTTPNotFound
        return batch_definition

    def get_mode_name_from(self, request):
        matchdict = request.matchdict
        mode_code = matchdict['mode_code']
        try:
            mode_name = MODE_NAME_BY_CODE[mode_code]
        except KeyError:
            raise HTTPNotFound
        return mode_name


def render_mode_dictionary(batch, base_uri, mode_name, for_print):
    automation_definition = batch.automation_definition
    css_uris = automation_definition.css_uris
    template_text = automation_definition.get_template_text(mode_name)
    variable_definitions = automation_definition.get_variable_definitions(
        mode_name, with_all=True)
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    i = count()
    render_html = partial(
        _render_html, variable_definitions=variable_definitions,
        batch=batch, m=m, i=i, base_uri=base_uri, mode_name=mode_name,
        for_print=for_print)
    return m | {
        'body_text': get_html_from_markdown(VARIABLE_ID_PATTERN.sub(
            render_html, template_text)),
        'js_text': '\n'.join(m['js_texts'])}


def _render_html(
        match, variable_definitions, batch, m, i, base_uri, mode_name,
        for_print):
    matching_text = match.group(0)
    terms = match.group(1).split('|')
    variable_id = terms[0].strip()
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id)
    except StopIteration:
        L.warning(
            '%s variable in template but not in configuration', variable_id)
        return matching_text
    view = VariableView.get_from(variable_definition)
    element = Element(f'v{next(i)}', base_uri, mode_name, for_print, terms[1:])
    rendered_element = view.render(batch, element)
    for k, v in m.items():
        extend_uniquely(v, [_.strip() for _ in rendered_element[k]])
    return rendered_element['body_text']


L = getLogger(__name__)

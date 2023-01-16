# TODO: Show runs with command line option
# TODO: Add unit tests
import json
from functools import partial
from itertools import count
from logging import getLogger
from pathlib import Path
from time import time
from types import FunctionType

from invisibleroads_macros_disk import make_random_folder
from invisibleroads_macros_web.markdown import get_html_from_markdown
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound
from pyramid.response import FileResponse, Response

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    ID_LENGTH,
    IMAGES_FOLDER,
    MUTATION_ROUTE,
    RUN_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_NAME_BY_CODE,
    STEP_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VARIABLE_ROUTE)
from ..exceptions import CrossComputeDataError
from ..macros.iterable import extend_uniquely, find_item
from ..routines.authorization import AuthorizationGuard
from ..routines.batch import DiskBatch
from ..routines.configuration import BatchDefinition
from ..routines.variable import (
    Element,
    VariableView,
    load_file_text,
    parse_data_by_id)


class AutomationRoutes():

    def __init__(self, configuration, safe, environment, queue):
        self.configuration = configuration
        self.safe = safe
        self.environment = environment
        self.queue = queue

    def includeme(self, config):
        config.include(self.configure_root)
        config.include(self.configure_styles)
        config.include(self.configure_automations)
        config.include(self.configure_batches)
        config.include(self.configure_runs)

    def configure_root(self, config):
        configuration = self.configuration
        config.add_route('root', '/')
        config.add_route('icon', '/favicon.ico')

        config.add_view(
            self.see_root,
            request_method='GET',
            route_name='root',
            renderer=configuration.get_template_path('root'))
        config.add_view(
            self.see_icon,
            request_method='GET',
            route_name='icon')

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
            renderer='crosscompute:templates/automation.html')

    def configure_batches(self, config):
        base_route = AUTOMATION_ROUTE + BATCH_ROUTE

        config.add_route(
            'automation batch',
            base_route)
        config.add_route(
            'automation batch step',
            base_route + STEP_ROUTE)
        config.add_route(
            'automation batch step variable json',
            base_route + STEP_ROUTE + VARIABLE_ROUTE + '.json')
        config.add_route(
            'automation batch step variable',
            base_route + STEP_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_step,
            request_method='GET',
            route_name='automation batch step',
            renderer='crosscompute:templates/step.html')
        config.add_view(
            self.see_automation_batch_step_variable_json,
            request_method='GET',
            route_name='automation batch step variable json',
            renderer='json')
        config.add_view(
            self.see_automation_batch_step_variable,
            request_method='GET',
            route_name='automation batch step variable')

    def configure_runs(self, config):
        base_route = AUTOMATION_ROUTE + RUN_ROUTE

        config.add_route(
            'automation run',
            base_route)
        config.add_route(
            'automation run step',
            base_route + STEP_ROUTE)
        config.add_route(
            'automation run step variable json',
            base_route + STEP_ROUTE + VARIABLE_ROUTE + '.json')
        config.add_route(
            'automation run step variable',
            base_route + STEP_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_step,
            request_method='GET',
            route_name='automation run step',
            renderer='crosscompute:templates/step.html')
        config.add_view(
            self.see_automation_batch_step_variable_json,
            request_method='GET',
            route_name='automation run step variable json',
            renderer='json')
        config.add_view(
            self.see_automation_batch_step_variable,
            request_method='GET',
            route_name='automation run step variable')

    def see_root(self, request):
        'Render root with a list of available automations'
        configuration = self.configuration
        guard = AuthorizationGuard(request, self.safe)
        if not guard.check('see_root', configuration):
            raise HTTPForbidden
        return {
            'title_text': configuration.get('name', 'Automations'),
            'automations': guard.get_automation_definitions(configuration),
            'css_uris': configuration.css_uris,
            'mutation_uri': MUTATION_ROUTE.format(uri=''),
            'mutation_timestamp': time(),
        }

    def see_icon(self, request):
        return FileResponse(IMAGES_FOLDER / 'favicon.ico')

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
        guard = AuthorizationGuard(
            request, self.safe, automation_definition.identities_by_token)
        if not guard.check('run_automation', automation_definition):
            raise HTTPForbidden
        variable_definitions = automation_definition.get_variable_definitions(
            'input')
        try:
            data_by_id = request.json_body
        except json.JSONDecodeError:
            data_by_id = {}
        try:
            data_by_id = parse_data_by_id(data_by_id, variable_definitions)
        except CrossComputeDataError as e:
            raise HTTPBadRequest(e)
        runs_folder = automation_definition.folder / 'runs'
        folder = Path(make_random_folder(runs_folder, ID_LENGTH))
        guard.save_identities(folder / 'debug' / 'identities.dictionary')
        batch_definition = BatchDefinition({
            'folder': folder,
        }, data_by_id=data_by_id, is_run=True)
        self.queue.put((
            automation_definition, batch_definition, self.environment))
        automation_definition.run_definitions.append(batch_definition)
        step_code = 'l' if automation_definition.get_variable_definitions(
            'log') else 'o'
        return {'run_id': batch_definition.name, 'step_code': step_code}

    def see_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        guard = AuthorizationGuard(
            request, self.safe, automation_definition.identities_by_token)
        if not guard.check('see_automation', automation_definition):
            raise HTTPForbidden
        design_name = automation_definition.get_design_name('automation')
        automation_uri = automation_definition.uri
        if design_name == 'none':
            d = {'css_uris': automation_definition.css_uris}
            mutation_reference_uri = automation_uri
        else:
            batch_definition = automation_definition.batch_definitions[0]
            batch = DiskBatch(
                automation_definition, batch_definition, request.params)
            d = _get_step_page_dictionary(request, batch, design_name)
            mutation_reference_uri = _get_automation_batch_step_uri(
                automation_definition, batch_definition, design_name)
        return d | {
            'name': automation_definition.name,
            'description': automation_definition.description,
            'host_uri': request.host_url,
            'uri': automation_uri,
            'batches': guard.get_batch_definitions(automation_definition),
            'runs': automation_definition.run_definitions,
            'title_text': automation_definition.name,
            'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
            'mutation_timestamp': time(),
        }

    def see_automation_batch_step(self, request):
        automation_definition = self.get_automation_definition_from(request)
        guard = AuthorizationGuard(
            request, self.safe, automation_definition.identities_by_token)
        is_match = guard.check('see_batch', automation_definition)
        if not is_match:
            raise HTTPForbidden
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        batch = DiskBatch(
            automation_definition, batch_definition, request.params)
        if isinstance(is_match, FunctionType) and not is_match(batch):
            raise HTTPForbidden
        step_name = _get_step_name(request)
        return _get_step_page_dictionary(request, batch, step_name)

    def see_automation_batch_step_variable_json(self, request):
        data, definition, batch = self.get_variable_pack_from(request)
        if 'path' in data:
            value = load_file_text(data['path'])
        else:
            value = data['value']
        configuration = batch.get_variable_configuration(definition).copy()
        configuration.pop('path', None)
        return {'value': value, 'configuration': configuration}

    def see_automation_batch_step_variable(self, request):
        data = self.get_variable_pack_from(request)[0]
        if 'path' in data:
            return FileResponse(data['path'], request=request)
        else:
            return Response(str(data['value']))

    def get_automation_definition_from(self, request):
        matchdict = request.matchdict
        automation_definitions = self.configuration.automation_definitions
        automation_slug = matchdict['automation_slug']
        try:
            automation_definition = find_item(
                automation_definitions, 'slug', automation_slug,
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

    def get_variable_pack_from(self, request):
        automation_definition = self.get_automation_definition_from(request)
        guard = AuthorizationGuard(
            request, self.safe, automation_definition.identities_by_token)
        is_match = guard.check('see_batch', automation_definition)
        if not is_match:
            raise HTTPForbidden
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        batch = DiskBatch(automation_definition, batch_definition)
        if isinstance(is_match, FunctionType) and not is_match(batch):
            raise HTTPForbidden
        step_name = _get_step_name(request)
        variable_id = request.matchdict['variable_id']
        variable_definition = _get_variable_definition(
            automation_definition, step_name, variable_id)
        variable_data = batch.get_data(variable_definition)
        if 'error' in variable_data:
            raise HTTPNotFound
        return variable_data, variable_definition, batch


def _get_step_name(request):
    matchdict = request.matchdict
    step_code = matchdict['step_code']
    try:
        step_name = STEP_NAME_BY_CODE[step_code]
    except KeyError:
        raise HTTPNotFound
    return step_name


def _get_variable_definition(automation_definition, step_name, variable_id):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPNotFound
    return variable_definition


def _get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name):
    automation_uri = automation_definition.uri
    batch_uri = batch_definition.uri
    step_code = STEP_CODE_BY_NAME[step_name]
    step_uri = STEP_ROUTE.format(step_code=step_code)
    return automation_uri + batch_uri + step_uri


def _get_step_page_dictionary(request, batch, step_name):
    params = request.params
    automation_definition = batch.automation_definition
    batch_definition = batch.batch_definition
    design_name = automation_definition.get_design_name(step_name)
    root_uri = request.registry.settings['root_uri']
    mutation_reference_uri = _get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    return {
        'title_text': batch_definition.name,
        'automation_definition': automation_definition,
        'batch_definition': batch_definition,
        'step_name': step_name,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
        'mutation_timestamp': time(),
    } | __get_step_page_dictionary(
        batch, root_uri, step_name, design_name, for_embed='_embed' in params,
        for_print='_print' in params)


def __get_step_page_dictionary(
        batch, root_uri, step_name, design_name, for_embed, for_print):
    automation_definition = batch.automation_definition
    css_uris = automation_definition.css_uris
    template_text = automation_definition.get_template_text(
        step_name)
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    i = count()
    render_html = partial(
        _render_html, variable_definitions=variable_definitions,
        batch=batch, m=m, i=i, root_uri=root_uri, design_name=design_name,
        for_print=for_print)
    main_text = get_html_from_markdown(VARIABLE_ID_TEMPLATE_PATTERN.sub(
        render_html, template_text))
    return m | {
        'css_text': __get_css_text(design_name, for_embed, for_print),
        'main_text': main_text,
        'js_text': '\n'.join(m['js_texts']),
        'for_embed': for_embed,
    }


def __get_css_text(design_name, for_embed, for_print):
    css_texts = []
    if not for_embed and not for_print:
        css_texts.append(HEADER_CSS)
    elif for_embed:
        css_texts.append(EMBED_CSS)
    if design_name == 'flex-vertical':
        css_texts.append(FLEX_VERTICAL_CSS)
    return '\n'.join(css_texts)


def _render_html(
        match, variable_definitions, batch, m, i, root_uri, design_name,
        for_print):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'ROOT_URI':
        return root_uri
    terms = matching_inner_text.split('|')
    variable_id = terms[0].strip()
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id)
    except StopIteration:
        L.warning(
            '%s variable in template but not in configuration', variable_id)
        matching_outer_text = match.group(0)
        return matching_outer_text
    view = VariableView.get_from(variable_definition)
    element = Element(
        f'v{next(i)}', root_uri, design_name, for_print, terms[1:])
    page_dictionary = view.render(batch, element)
    for k, v in m.items():
        extend_uniquely(v, [_.strip() for _ in page_dictionary[k]])
    return page_dictionary['main_text']


EMBED_CSS = '''\
body {
  margin: 0;
}
'''
HEADER_CSS = '''\
header {
  margin-bottom: 16px;
}
@media print {
  header {
    display: none;
  }
}'''
FLEX_VERTICAL_CSS = '''\
main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
main > * {
  margin: 0;
}
._view {
  display: flex;
  flex-direction: column;
}
._view img {
  align-self: start;
  max-width: 100%;
}
#_run {
  padding: 8px 0;
}'''
L = getLogger(__name__)

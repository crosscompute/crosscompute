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
        guard = AuthorizationGuard(request, self.safe)
        if not guard.check('see_root', configuration):
            raise HTTPForbidden
        return {
            'automations': guard.get_automation_definitions(configuration),
            'css_uris': configuration.css_uris,
            'mutation_uri': MUTATION_ROUTE.format(uri=''),
            'mutation_timestamp': time(),
        }

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
        if design_name == 'none':
            d = {'css_uris': automation_definition.css_uris}
            mutation_reference_uri = automation_uri
        else:
            batch_definition = automation_definition.batch_definitions[0]
            batch = DiskBatch(
                automation_definition, batch_definition, request.params)
            d = _get_step_page_dictionary(request, batch, design_name)
        return d | {
            'batches': guard.get_batch_definitions(automation_definition),
        }

    def see_automation_batch_step(self, request):
        # automation_definition = self.get_automation_definition_from(request)
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
        # step_name = _get_step_name(request)
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

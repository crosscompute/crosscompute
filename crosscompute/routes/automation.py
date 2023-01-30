# TODO: Show runs with command line option
# TODO: Add unit tests
from time import time
from types import FunctionType

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound
from pyramid.response import FileResponse, Response

from ..constants import (
    MUTATION_ROUTE)
from ..exceptions import CrossComputeDataError
from ..routines.authorization import AuthorizationGuard
from ..routines.batch import DiskBatch
from ..routines.variable import (
    load_file_text,
    parse_data_by_id)


class AutomationRoutes():

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
        guard = AuthorizationGuard(
            request, self.safe, automation_definition.identities_by_token)
        if not guard.check('run_automation', automation_definition):
            raise HTTPForbidden
        variable_definitions = automation_definition.get_variable_definitions(
            'input')
        try:
            # TODO: Use fastapi validation
            data_by_id = parse_data_by_id(data_by_id, variable_definitions)
        except CrossComputeDataError as e:
            raise HTTPBadRequest(e)
        # runs_folder = automation_definition.folder / 'runs'
        # folder = Path(make_random_folder(runs_folder, ID_LENGTH))
        guard.save_identities(folder / 'debug' / 'identities.dictionary')

    def see_automation(self, request):
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
            batch = DiskBatch(automation_definition, batch_definition)
            d = _get_step_page_dictionary(request, batch, design_name)
        return d | {
            'batches': guard.get_batch_definitions(automation_definition),
        }

    def see_automation_batch_step(self, request):
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
        variable_data = batch.load_data(variable_definition)
        if 'error' in variable_data:
            raise HTTPNotFound
        return variable_data, variable_definition, batch

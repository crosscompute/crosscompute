from logging import getLogger
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import FileResponse
from invisibleroads_macros_disk import make_random_folder

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    ID_LENGTH,
    MUTATION_ROUTE,
    STEP_ROUTE,
    VARIABLE_ROUTE)
from ..dependencies import (
    AuthorizationGuardFactory,
    get_automation_definition,
    get_batch_definition,
    get_data_by_id,
    get_step_name,
    get_variable_definition)
from ..routines.authorization import AuthorizationGuard
from ..routines.batch import DiskBatch
from ..routines.configuration import (
    AutomationDefinition,
    BatchDefinition,
    VariableDefinition)
from ..routines.step import (
    get_automation_batch_step_uri,
    get_step_page_dictionary)
from ..routines.variable import load_file_text
from ..settings import (
    TemplateResponse,
    site,
    template_path_by_id)


router = APIRouter()


@router.get(
    AUTOMATION_ROUTE,
    tags=['automation'])
async def see_automation(
    request: Request,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_automation')),
):
    automation_uri = automation_definition.uri
    design_name = automation_definition.get_design_name('automation')
    mutation_reference_uri = automation_uri
    if design_name == 'none':
        d = {'css_uris': automation_definition.css_uris}
        # is_done = 1
    else:
        batch_definition = automation_definition.batch_definitions[0]
        d = get_step_page_dictionary(
            automation_definition, batch_definition, design_name,
            request.query_params)
        # is_done = batch.is_done()
    request_uri = request.url
    # TODO: change is_done if interval defined
    return TemplateResponse(template_path_by_id['automation'], {
        'request': request,
        'title_text': automation_definition.name,
        'description': automation_definition.description,
        'host_uri': request_uri.scheme + '://' + request_uri.netloc,
        'name': automation_definition.name,
        'uri': automation_uri,
        'automation_definition': automation_definition,
        'step_name': design_name,
        'batches': guard.get_batch_definitions(automation_definition),
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
        'mutation_timestamp': time(),
    } | d)


@router.post(
    AUTOMATION_ROUTE + '.json',
    tags=['automation'])
async def run_automation_json(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    data_by_id: dict = Depends(
        get_data_by_id),
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('run_automation')),
):
    runs_folder = automation_definition.folder / 'runs'
    folder = Path(make_random_folder(runs_folder, ID_LENGTH))
    batch_definition = BatchDefinition({
        'folder': folder}, data_by_id=data_by_id, is_run=True)
    guard.save_identities(folder / 'debug' / 'identities.dictionary')

    queue = site['queue']
    environment = site['environment']
    queue.put((automation_definition, batch_definition, environment))
    automation_definition.batch_definitions.append(batch_definition)

    step_code = 'l' if automation_definition.get_variable_definitions(
        'log') else 'o'
    return {
        'batch_slug': batch_definition.name,
        'step_code': step_code}


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE,
    tags=['automation'])
async def see_automation_batch(
    request: Request,
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_batch')),
):
    return TemplateResponse(template_path_by_id['batch'], {
        'request': request})


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE,
    tags=['automation'])
async def see_automation_batch_step(
    request: Request,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    batch_definition: BatchDefinition = Depends(get_batch_definition),
    step_name: str = Depends(get_step_name),
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_batch')),
):
    mutation_reference_uri = get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    page_dictionary = get_step_page_dictionary(
        automation_definition, batch_definition, step_name,
        request.query_params)
    # is_done = batch.is_done()
    # TODO: change is_done if interval defined
    # TODO: check is_done
    return TemplateResponse(template_path_by_id['step'], {
        'request': request,
        'title_text': batch_definition.name,
        'automation_definition': automation_definition,
        'batch_definition': batch_definition,
        'step_name': step_name,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
        'mutation_timestamp': time(),
    } | page_dictionary)


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE + VARIABLE_ROUTE + '.json',
    tags=['automation'])
async def see_automation_batch_step_variable_json(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    batch_definition: BatchDefinition = Depends(get_batch_definition),
    variable_definition: VariableDefinition = Depends(
        get_variable_definition),
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_batch')),
):
    batch = DiskBatch(automation_definition, batch_definition)
    variable_data = batch.load_data(variable_definition)
    if 'error' in variable_data:
        raise HTTPException(status_code=404)
    if 'path' in variable_data:
        variable_value = load_file_text(variable_data['path'])
    else:
        variable_value = variable_data['value']
    variable_configuration = batch.get_variable_configuration(
        variable_definition).copy()
    variable_configuration.pop('path', None)
    return {
        'value': variable_value,
        'configuration': variable_configuration}


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
async def see_automation_batch_step_variable(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    batch_definition: BatchDefinition = Depends(get_batch_definition),
    variable_definition: VariableDefinition = Depends(
        get_variable_definition),
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_batch')),
):
    batch = DiskBatch(automation_definition, batch_definition)
    variable_data = batch.load_data(variable_definition)
    if 'error' in variable_data:
        raise HTTPException(status_code=404)
    if 'path' in variable_data:
        response = FileResponse(variable_data['path'])
    else:
        response = Response(str(variable_data['value']))
    return response


L = getLogger(__name__)

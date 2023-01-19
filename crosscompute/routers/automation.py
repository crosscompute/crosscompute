from functools import partial
from itertools import count
from logging import getLogger
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import FileResponse
from invisibleroads_macros_disk import make_random_folder
from invisibleroads_macros_web.markdown import get_html_from_markdown

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    EMBED_CSS,
    FLEX_VERTICAL_CSS,
    HEADER_CSS,
    ID_LENGTH,
    MUTATION_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VARIABLE_ROUTE)
from ..dependencies import (
    get_automation_definition,
    get_batch_definition,
    get_data_by_id,
    get_step_name)
from ..macros.iterable import extend_uniquely, find_item
from ..routines.batch import DiskBatch
from ..routines.configuration import (
    AutomationDefinition,
    BatchDefinition)
from ..routines.variable import (
    Element,
    VariableView)
from ..variables import (
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
):
    return TemplateResponse(template_path_by_id['automation'], {
        'request': request,
        'title_text': automation_definition.name,
        'description': automation_definition.description,
        'host_uri': request.url,
        'name': automation_definition.name,
        'uri': automation_definition.uri,
        'batches': automation_definition.batch_definitions,
    })


@router.post(
    AUTOMATION_ROUTE + '.json',
    tags=['automation'])
async def run_automation_json(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    data_by_id: dict = Depends(
        get_data_by_id),
):
    runs_folder = automation_definition.folder / 'runs'
    folder = Path(make_random_folder(runs_folder, ID_LENGTH))
    batch_definition = BatchDefinition({
        'folder': folder}, data_by_id=data_by_id, is_run=True)

    queue = site['queue']
    environment = site['environment']
    queue.put((automation_definition, batch_definition, environment))
    automation_definition.batch_definitions.append(batch_definition)

    step_code = 'l' if automation_definition.get_variable_definitions(
        'log') else 'o'
    return {
        'run_id': batch_definition.name,
        'step_code': step_code,
    }


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE,
    tags=['automation'])
async def see_automation_batch(request: Request):
    return TemplateResponse(template_path_by_id['batch'], {
        'request': request,
    })


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE,
    tags=['automation'])
async def see_automation_batch_step(
    request: Request,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    batch_definition: BatchDefinition = Depends(
        get_batch_definition),
    step_name: str = Depends(
        get_step_name),
):
    return TemplateResponse(template_path_by_id['step'], {
        'request': request,
        'title_text': batch_definition.name,
        'automation_definition': automation_definition,
        'batch_definition': batch_definition,
        'step_name': step_name,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
        'mutation_timestamp': time(),
        'css_uris': m['css_uris'],
        'css_text': get_css_text(design_name, for_embed, for_print),
        'main_text': main_text,
        'js_uris': m['js_uris'],
        'js_text': '\n'.join(m['js_texts']),
        'for_embed': for_embed,
    })


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
async def see_automation_batch_step_variable(
    variable_id: str,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    batch_definition: BatchDefinition = Depends(
        get_batch_definition),
    step_name: str = Depends(
        get_step_name),
):
    batch = DiskBatch(automation_definition, batch_definition)
    variable_definition = get_variable_definition(
        automation_definition, step_name, variable_id)
    data = batch.get_data(variable_definition)
    if 'error' in data:
        raise HTTPException(status_code=404)
    if 'path' in data:
        response = FileResponse(data['path'])
    else:
        response = Response(str(data['value']))
    return response


def get_step_response(automation_definition, batch_definition, request):
    root_uri = template_environment.globals['root_uri']
    get_step_page_outer_dictionary(automation_definition, batch_definition)


def get_step_page_outer_dictionary(batch, step_name, request_params):
    design_name = automation_definition.get_design_name(step_name)
    # TODO: get root_uri from globals
    # TODO: pass params
    root_uri = ''
    # root_uri = request.registry.settings['root_uri']
    mutation_reference_uri = _get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    for_embed='_embed' in params
    for_print='_print' in params

    css_uris = automation_definition.css_uris
    template_text = automation_definition.get_template_text(
        step_name)
    variable_definitions = automation_definition.get_variable_definitions(
        step_name, with_all=True)
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    i = count()
    # TODO: pass params here
    render_element_html = partial(
        render_html, variable_definitions, batch, m, i, root_uri,
        design_name, for_print)
    main_text = get_html_from_markdown(VARIABLE_ID_TEMPLATE_PATTERN.sub(
        render_element_html, template_text))
    return m | {
    }


def get_css_text(design_name, for_embed, for_print):
    css_texts = []
    if not for_embed and not for_print:
        css_texts.append(HEADER_CSS)
    elif for_embed:
        css_texts.append(EMBED_CSS)
    if design_name == 'flex-vertical':
        css_texts.append(FLEX_VERTICAL_CSS)
    return '\n'.join(css_texts)


def get_variable_definition(automation_definition, step_name, variable_id):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPException(status_code=404)
    return variable_definition


def get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name):
    automation_uri = automation_definition.uri
    batch_uri = batch_definition.uri
    step_code = STEP_CODE_BY_NAME[step_name]
    step_uri = STEP_ROUTE.format(step_code=step_code)
    return automation_uri + batch_uri + step_uri


L = getLogger(__name__)

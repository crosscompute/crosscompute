from itertools import count
from functools import partial
from logging import getLogger
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, Request
from invisibleroads_macros_disk import make_random_folder
from invisibleroads_macros_web.markdown import get_html_from_markdown

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    ID_LENGTH,
    MUTATION_ROUTE,
    RUN_ROUTE,
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
    site_variables,
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
    automation_uri = automation_definition.uri
    return TemplateResponse(template_path_by_id['automation'], {
        'request': request,
        'title_text': automation_definition.name,
        'description': automation_definition.description,
        'host_uri': request.url,
        'name': automation_definition.name,
        'uri': automation_uri,
        'batches': automation_definition.batch_definitions,
    })


@router.post(
    AUTOMATION_ROUTE + '.json',
    tags=['automation'])
async def run_automation(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    data_by_id: dict = Depends(
        get_data_by_id),
):
    runs_folder = automation_definition.folder / 'runs'
    folder = Path(make_random_folder(runs_folder, ID_LENGTH))
    batch_definition = BatchDefinition({
        'folder': folder}, data_by_id=data_by_id, is_run=True)

    queue = site_variables['queue']
    environment = site_variables['environment']
    queue.put((automation_definition, batch_definition, environment))
    automation_definition.run_definitions.append(batch_definition)

    step_code = 'l' if automation_definition.get_variable_definitions(
        'log') else 'o'
    return {
        'run_id': batch_definition.name, 'step_code': step_code,
    }


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE,
    tags=['automation'])
@router.get(
    AUTOMATION_ROUTE + RUN_ROUTE,
    tags=['automation'])
async def see_automation_batch(request: Request):
    return TemplateResponse(template_path_by_id['batch'], {
        'request': request,
    })


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE,
    tags=['automation'])
@router.get(
    AUTOMATION_ROUTE + RUN_ROUTE + STEP_ROUTE,
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
    batch = DiskBatch(
        automation_definition, batch_definition, request.query_params)
    return TemplateResponse(
        template_path_by_id['step'],
        _get_step_page_dictionary(request, batch, step_name))


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
@router.get(
    AUTOMATION_ROUTE + RUN_ROUTE + STEP_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
async def see_automation_batch_step_variable(request: Request):
    return {}


def _get_step_page_dictionary(request, batch, step_name):
    params = request.query_params
    automation_definition = batch.automation_definition
    batch_definition = batch.batch_definition
    design_name = automation_definition.get_design_name(step_name)
    root_uri = ''
    # root_uri = request.registry.settings['root_uri']
    mutation_reference_uri = _get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    return {
        'request': request,
        'title_text': batch_definition.name,
        'automation_definition': automation_definition,
        'batch_definition': batch_definition,
        'step_name': step_name,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri),
        'mutation_timestamp': time(),
    } | __get_step_page_dictionary(
        batch, root_uri, step_name, design_name, for_embed='_embed' in params,
        for_print='_print' in params)


def _get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name):
    automation_uri = automation_definition.uri
    batch_uri = batch_definition.uri
    step_code = STEP_CODE_BY_NAME[step_name]
    step_uri = STEP_ROUTE.format(step_code=step_code)
    return automation_uri + batch_uri + step_uri


def __get_step_page_dictionary(
        batch, root_uri, step_name, design_name, for_embed, for_print):
    automation_definition = batch.automation_definition
    css_uris = automation_definition.css_uris
    template_text = automation_definition.get_template_text(
        step_name)
    variable_definitions = automation_definition.get_variable_definitions(
        step_name, with_all=True)
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    i = count()
    render_html = partial(
        _render_html, variable_definitions=variable_definitions,
        batch=batch, m=m, i=i, root_uri=root_uri, design_name=design_name,
        for_print=for_print)
    main_text = get_html_from_markdown(VARIABLE_ID_TEMPLATE_PATTERN.sub(
        render_html, template_text))
    return m | {
        'css_text': _get_css_text(design_name, for_embed, for_print),
        'main_text': main_text,
        'js_text': '\n'.join(m['js_texts']),
        'for_embed': for_embed,
    }


def _render_html(
        match, variable_definitions, batch, m, i, root_uri, design_name,
        for_print):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'root_uri':
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


def _get_css_text(design_name, for_embed, for_print):
    css_texts = []
    if not for_embed and not for_print:
        css_texts.append(HEADER_CSS)
    elif for_embed:
        css_texts.append(EMBED_CSS)
    if design_name == 'flex-vertical':
        css_texts.append(FLEX_VERTICAL_CSS)
    return '\n'.join(css_texts)


EMBED_CSS = '''\
body {
  margin: 0;
}'''
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

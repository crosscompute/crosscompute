from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from ..constants import (
    ASSETS_FOLDER,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    MUTATION_ROUTE,
    STEP_ROUTE,
    STYLE_ROUTE)
from ..dependencies import (
    AuthorizationGuardFactory,
    get_automation_definition,
    get_batch_definition)
from ..macros.iterable import (
    find_item)
from ..routines.authorization import AuthorizationGuard
from ..routines.configuration import (
    AutomationDefinition)
from ..settings import (
    TemplateResponse,
    site,
    template_globals,
    template_path_by_id)


router = APIRouter()


@router.api_route(AUTOMATION_ROUTE + BATCH_ROUTE + STEP_ROUTE, methods=[
    'HEAD',
], dependencies=[
    Depends(get_automation_definition),
    Depends(get_batch_definition),
], tags=['root'])
@router.api_route(AUTOMATION_ROUTE + BATCH_ROUTE, methods=[
    'HEAD',
], dependencies=[
    Depends(get_automation_definition),
    Depends(get_batch_definition),
], tags=['root'])
@router.api_route(AUTOMATION_ROUTE, methods=[
    'HEAD',
], dependencies=[
    Depends(get_automation_definition),
], tags=['root'])
@router.api_route('/', methods=[
    'HEAD',
], tags=['root'])
async def check():
    return Response()


@router.get('/', tags=['root'])
async def see_root(
    request: Request,
    response: Response,
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('see_root')),
):
    'Render root with a list of available automations'
    configuration = site['configuration']
    return TemplateResponse(template_path_by_id['root'], {
        'request': request,
        'title_text': site['name'],
        'css_uris': configuration.css_uris,
        'automation_definitions': guard.get_automation_definitions(
            configuration),
        'mutation_uri': MUTATION_ROUTE.format(uri=''),
        'mutation_timestamp': time(),
    }, headers=response.headers)


@router.get('/favicon.ico', tags=['root'])
async def see_icon(response: Response):
    return FileResponse(
        ASSETS_FOLDER / 'favicon.ico', headers=response.headers)


@router.get(STYLE_ROUTE, tags=['root'])
async def see_style(request: Request, response: Response):
    return get_style_response(
        site['configuration'], request.url.path, response.headers)


@router.get(AUTOMATION_ROUTE + STYLE_ROUTE, tags=['root'])
async def see_automation_style(
    request: Request,
    response: Response,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
):
    return get_style_response(
        automation_definition, request.url.path, response.headers)


def get_style_response(automation_definition, uri_path, response_headers):
    style_definitions = automation_definition.style_definitions
    if site['with_prefix']:
        uri_path = uri_path.replace(template_globals['root_uri'], '', 1)
    try:
        style_definition = find_item(style_definitions, 'uri', uri_path)
    except StopIteration:
        raise HTTPException(status_code=404)
    path = automation_definition.folder / style_definition['path']
    try:
        response = FileResponse(path)
    except TypeError:
        raise HTTPException(status_code=404)
    return response

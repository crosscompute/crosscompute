from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    IMAGES_FOLDER,
    STYLE_ROUTE)
from ..dependencies import (
    get_automation_definition)
from ..macros.iterable import (
    find_item)
from ..routines.configuration import (
    AutomationDefinition)
from ..settings import (
    TemplateResponse,
    site,
    template_path_by_id)


router = APIRouter()


@router.get('/', tags=['root'])
async def see_root(request: Request):
    'Render root with a list of available automations'
    return TemplateResponse(template_path_by_id['root'], {
        'request': request,
        'title_text': site['name'],
        'automation_definitions': site['definitions'],
    })


@router.get('/favicon.ico', tags=['root'])
async def see_icon():
    return FileResponse(IMAGES_FOLDER / 'favicon.ico')


@router.get(STYLE_ROUTE, tags=['root'])
async def see_style(request: Request):
    return get_style_response(site['configuration'], request.url.path)


@router.get(AUTOMATION_ROUTE + STYLE_ROUTE, tags=['root'])
async def see_automation_style(
    request: Request,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
):
    return get_style_response(automation_definition, request.url.path)


def get_style_response(automation_definition, uri_path):
    style_definitions = automation_definition.style_definitions
    try:
        style_definition = find_item(
            style_definitions, 'uri', uri_path)
    except StopIteration:
        raise HTTPException(status_code=404)
    path = automation_definition.folder / style_definition['path']
    try:
        response = FileResponse(path)
    except TypeError:
        raise HTTPException(status_code=404)
    return response

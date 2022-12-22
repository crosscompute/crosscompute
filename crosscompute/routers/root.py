from fastapi import APIRouter, HTTPException, Path, Request, Response
from fastapi.responses import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    IMAGES_FOLDER,
    STYLE_ROUTE)
from ..variables import (
    TemplateResponse,
    automation_definitions,
    site_variables,
    template_path_by_id)


router = APIRouter()


@router.get(
    '/',
    tags=['root'])
async def see_root(request: Request):
    'Render root with a list of available automations'
    return TemplateResponse(template_path_by_id['root'], {
        'request': request,
        'title_text': site_variables['name'],
        'automation_definitions': automation_definitions,
    })


@router.get(
    '/favicon.ico',
    tags=['root'])
async def see_icon():
    return FileResponse(IMAGES_FOLDER / 'favicon.ico')


@router.get(
    STYLE_ROUTE,
    tags=['root'])
async def see_style(request: Request):
    import pudb.forked; pudb.forked.set_trace()
    automation_definition = self.configuration
    try:
        style_definition = find_item(
            style_definitions, 'uri', request.environ['PATH_INFO'])
    except StopIteration:
        raise HTTPNotFound
    path = automation_definition.folder / style_definition['path']
    try:
        response = FileResponse(path, request)
    except TypeError:
        raise HTTPException(status_code=404)
    return response


@router.get(
    AUTOMATION_ROUTE + STYLE_ROUTE,
    tags=['root'])
async def see_automation_style(request: Request, automation_slug: str):
    automation_definition = self.get_automation_definition_from(
        request)
    try:
        style_definition = find_item(
            style_definitions, 'uri', request.environ['PATH_INFO'])
    except StopIteration:
        raise HTTPException(status_code=404)
    print(automation_slug)
    path = automation_definition.folder / style_definition['path']
    try:
        response = FileResponse(path, request)
    except TypeError:
        raise HTTPException(status_code=404)
    return response

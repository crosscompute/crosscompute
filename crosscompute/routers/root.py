from fastapi import APIRouter, Path, Request
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
@router.get(
    AUTOMATION_ROUTE + STYLE_ROUTE,
    tags=['root'])
# async def see_style(automation_slug: str | None = Path(default=None)):
async def see_style(automation_slug: str | None = None):
# async def see_style(automation_slug: Optional[str] = Path(default=None)):
    print(automation_slug)
    from fastapi import Response
    return Response('')

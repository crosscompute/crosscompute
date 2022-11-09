from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ..constants import (
    IMAGES_FOLDER)
from ..variables import (
    TemplateResponse,
    automation_definitions,
    site_settings,
    template_path_by_id)


router = APIRouter()


@router.get('/', tags=['root'])
async def see_root(request: Request):
    'Render root with a list of available automations'
    return TemplateResponse(template_path_by_id['root'], {
        'request': request,
        'title_text': site_settings['name'],
        'automation_definitions': automation_definitions,
    })


@router.get('/favicon.ico', tags=['root'])
async def see_icon():
    return FileResponse(IMAGES_FOLDER / 'favicon.ico')

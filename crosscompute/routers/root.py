from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ..constants import (
    IMAGES_FOLDER)
from ..variables import (
    TemplateResponse,
    template_path_by_id)


router = APIRouter()


@router.get('/', tags=['root'])
async def see_root(request: Request):
    # template_path = configuration.get_template_path('root')
    template_path = template_path_by_id['root']
    return TemplateResponse(template_path, {'request': request})


@router.get('/favicon.ico', tags=['root'])
async def see_icon():
    return FileResponse(IMAGES_FOLDER / 'favicon.ico')


'''
config.add_view(
    renderer=configuration.get_template_path('root'))
config.add_route(
    'style', STYLE_ROUTE)
'''

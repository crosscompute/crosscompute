from fastapi import APIRouter, Depends, Request

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    MODE_ROUTE,
    RUN_ROUTE,
    VARIABLE_ROUTE)
from ..dependencies.automation import (
    get_automation_definition)
from ..routines.configuration import (
    AutomationDefinition)
from ..variables import (
    TemplateResponse,
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
async def run_automation():
    return {
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
    AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE,
    tags=['automation'])
@router.get(
    AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE,
    tags=['automation'])
async def see_automation_batch_mode(request: Request):
    return TemplateResponse(template_path_by_id['mode'], {
        'request': request,
    })


@router.get(
    AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
@router.get(
    AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE + VARIABLE_ROUTE,
    tags=['automation'])
async def see_automation_batch_mode_variable(request: Request):
    return {}

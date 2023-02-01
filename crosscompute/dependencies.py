from fastapi import Body, Depends, HTTPException, Request

from .constants import STEP_NAME_BY_CODE
from .exceptions import CrossComputeDataError
from .macros.iterable import find_item
from .routines.authorization import AuthorizationGuard
from .routines.configuration import AutomationDefinition
from .routines.variable import parse_data_by_id
from .settings import site


async def get_automation_definition(
    automation_slug: str | None = None,
):
    if not automation_slug:
        return
    automation_definitions = site['definitions']
    try:
        automation_definition = find_item(
            automation_definitions, 'slug', automation_slug,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPException(status_code=404)
    return automation_definition


async def get_batch_definition(
    batch_slug: str,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
):
    batch_definitions = getattr(automation_definition, 'batch_definitions')
    try:
        batch_definition = find_item(batch_definitions, 'slug', batch_slug)
    except StopIteration:
        raise HTTPException(status_code=404)
    return batch_definition


async def get_step_name(step_code: str):
    try:
        step_name = STEP_NAME_BY_CODE[step_code]
    except KeyError:
        raise HTTPException(status_code=404)
    return step_name


async def get_data_by_id(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    data_by_id: dict = Body,
):
    variable_definitions = automation_definition.get_variable_definitions(
        'input')
    try:
        data_by_id = parse_data_by_id(data_by_id, variable_definitions)
    except CrossComputeDataError as e:
        raise HTTPException(status_code=400, detail=e.args[0])
    return data_by_id


async def get_authorization_token(request: Request):
    params = request.query_params
    headers = request.headers
    cookies = request.cookies
    if '_token' in params:
        token = params['_token']
        request.response.set_cookie(
            'crosscompute-token', value=token, secure=True, httponly=True,
            samesite='none')
    elif 'Authorization' in headers:
        try:
            token = headers['Authorization'].split(maxsplit=1)[1]
        except IndexError:
            token = ''
    elif 'crosscompute-token' in cookies:
        token = cookies['crosscompute-token']
    else:
        token = ''
    return token


async def get_authorization_identities(
    request: Request,
    token: str = Depends(
        get_authorization_token),
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
):
    identities = {}
    if token:
        try:
            d = site['safe'].get(token)
        except KeyError:
            if automation_definition:
                identities_by_token = automation_definition.identities_by_token
                d = identities_by_token.get(token, {})
            else:
                d = {}
        identities.update(d, ip_address=request.client.host)
    return identities


async def get_authorization_guard(
    identities: dict = Depends(
        get_authorization_identities),
):
    return AuthorizationGuard(identities)

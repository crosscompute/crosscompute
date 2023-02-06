from logging import getLogger
from types import FunctionType

from fastapi import Body, Depends, HTTPException, Request, Response

from .constants import STEP_NAME_BY_CODE
from .exceptions import CrossComputeDataError
from .macros.iterable import find_item
from .routines.authorization import AuthorizationGuard
from .routines.batch import DiskBatch
from .routines.configuration import AutomationDefinition, BatchDefinition
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
    batch_slug: str | None = None,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
):
    if not batch_slug:
        return
    batch_definitions = getattr(automation_definition, 'batch_definitions', [])
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


async def get_variable_definition(
    variable_id: str,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    step_name: str = Depends(get_step_name),
):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPException(status_code=404)
    return variable_definition


async def get_data_by_id(
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition),
    data_by_id: dict = Body(),
):
    variable_definitions = automation_definition.get_variable_definitions(
        'input')
    try:
        data_by_id = parse_data_by_id(data_by_id, variable_definitions)
    except CrossComputeDataError as e:
        raise HTTPException(status_code=400, detail=e.args[0])
    return data_by_id


async def get_authorization_token(request: Request, response: Response):
    params = request.query_params
    headers = request.headers
    cookies = request.cookies
    if '_token' in params:
        token = params['_token']
        if request['scheme'] == 'http':
            d = {}
            L.warning('setting insecure cookie')
        else:
            d = {'secure': True, 'samesite': 'none'}
        response.set_cookie(
            'crosscompute-token', value=token, path=None, httponly=True, **d)
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
            c = automation_definition if automation_definition else site[
                'configuration']
            d = c.identities_by_token.get(token, {})
        identities.update(d, ip_address=request.client.host)
    return identities


class AuthorizationGuardFactory():

    def __init__(self, permission_id):
        self.permission_id = permission_id

    async def __call__(
        self,
        identities: dict = Depends(
            get_authorization_identities),
        automation_definition: AutomationDefinition = Depends(
            get_automation_definition),
        batch_definition: BatchDefinition = Depends(get_batch_definition),
    ):
        guard = AuthorizationGuard(identities)
        permission_id = self.permission_id
        if automation_definition:
            is_match = guard.check(permission_id, automation_definition)
            if not is_match:
                raise HTTPException(status_code=403)
            if batch_definition:
                batch = DiskBatch(automation_definition, batch_definition)
                if isinstance(is_match, FunctionType) and not is_match(batch):
                    raise HTTPException(status_code=403)
        elif not guard.check(permission_id, site['configuration']):
            raise HTTPException(status_code=403)
        return guard


L = getLogger(__name__)

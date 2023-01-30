from fastapi import Body, Depends, HTTPException, Request

from .constants import STEP_NAME_BY_CODE
from .exceptions import CrossComputeDataError
from .macros.iterable import find_item
from .routines.authorization import AuthorizationGuard
from .routines.configuration import AutomationDefinition
from .routines.variable import parse_data_by_id
from .settings import site


async def get_automation_definition(automation_slug: str):
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


async def get_authorization_guard(request: Request):
    safe = site['safe']
    authorization_guard = AuthorizationGuard(request, safe)
    from pudb.forked import set_trace; set_trace()
    '''
    if not guard.check('add_token', self.configuration):
        raise HTTPForbidden

    'automations': guard.get_automation_definitions(configuration),
    'batches': guard.get_batch_definitions(automation_definition),
    is_match = guard.check('see_batch', automation_definition)

    guard.save_identities(folder / 'debug' / 'identities.dictionary')

    if not guard.check('see_root', configuration):
        raise HTTPForbidden

    guard = AuthorizationGuard(
        request, self.safe, automation_definition.identities_by_token)
    if not guard.check('run_automation', automation_definition):
        raise HTTPForbidden

    guard = AuthorizationGuard(
        request, self.safe, automation_definition.identities_by_token)
    if not guard.check('see_automation', automation_definition):
        raise HTTPForbidden
    '''
    return authorization_guard

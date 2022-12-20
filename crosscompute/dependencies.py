from fastapi import Body, Depends, HTTPException

from .constants import (
    STEP_NAME_BY_CODE)
from .exceptions import (
    CrossComputeDataError)
from .macros.iterable import (
    find_item)
from .routines.configuration import (
    AutomationDefinition)
from .routines.variable import (
    parse_data_by_id)
from .variables import (
    automation_definitions)


async def get_automation_definition(automation_slug: str):
    try:
        automation_definition = find_item(
            automation_definitions, 'slug', automation_slug,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPException(status_code=404)
    return automation_definition


async def get_batch_definition(
    batch_slug: str | None = None,
    run_slug: str | None = None,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition)
):
    if batch_slug:
        slug = batch_slug
        key = 'batch_definitions'
    else:
        slug = run_slug
        key = 'run_definitions'
    batch_definitions = getattr(automation_definition, key)
    try:
        batch_definition = find_item(batch_definitions, 'slug', slug)
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
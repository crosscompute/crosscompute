from fastapi import Depends

from ..routines.configuration import (
    AutomationDefinition)
from .automation import get_automation_definition


# def get_batch_definition(batch_slug: str, run_slug: str):
async def get_batch_definition(
    # batch_slug: str,
    # run_slug: str,
    automation_definition: AutomationDefinition = Depends(
        get_automation_definition)
):
    key = 'batch_definitions'
    batch_definitions = getattr(automation_definition, key)
    # !!!
    batch_definition = batch_definitions[0]
    return batch_definition

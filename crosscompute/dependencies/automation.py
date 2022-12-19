from fastapi import HTTPException

from ..macros.iterable import find_item
from ..variables import (
    automation_definitions)


async def get_automation_definition(automation_slug: str):
    try:
        automation_definition = find_item(
            automation_definitions, 'slug', automation_slug,
            normalize=str.casefold)
    except StopIteration:
        raise HTTPException(status_code=404)
    return automation_definition

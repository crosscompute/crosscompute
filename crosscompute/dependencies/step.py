from fastapi import HTTPException

from ..constants import STEP_NAME_BY_CODE


async def get_step_name(step_code: str):
    try:
        step_name = STEP_NAME_BY_CODE[step_code]
    except KeyError:
        raise HTTPException(status_code=404)
    return step_name

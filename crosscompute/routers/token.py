from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_authorization_guard
from ..routines.authorization import AuthorizationGuard
from ..settings import site


router = APIRouter()


@router.post(
    '/tokens.json',
    tags=['token'])
async def add_token(
    identities: dict,
    time_in_seconds: int,
    guard: AuthorizationGuard = Depends(
        get_authorization_guard),
):
    configuration = site['configuration']
    if not guard.check('add_token', configuration):
        raise HTTPException(status_code=403)
    token = guard.put(identities, time_in_seconds)
    return {'access_token': token, 'token_type': 'bearer'}

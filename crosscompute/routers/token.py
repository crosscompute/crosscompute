from fastapi import APIRouter, Depends

from ..dependencies import AuthorizationGuardFactory
from ..routines.authorization import AuthorizationGuard


router = APIRouter()


@router.post(
    '/tokens.json',
    tags=['token'])
async def add_token(
    identities: dict,
    time_in_seconds: int,
    guard: AuthorizationGuard = Depends(
        AuthorizationGuardFactory('add_token')),
):
    token = guard.put(identities, time_in_seconds)
    return {
        'access_token': token,
        'token_type': 'bearer',
    }

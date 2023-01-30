from fastapi import APIRouter, Depends

from ..dependencies import get_authorization_guard
from ..routines.authorization import AuthorizationGuard


router = APIRouter()


@router.post(
    '/tokens.json',
    tags=['token'])
async def add_token(
    authorization_guard: AuthorizationGuard = Depends(
        get_authorization_guard),
):
    return {}

from fastapi import APIRouter


router = APIRouter()


@router.post(
    'tokens.json',
    tags=['token'])
async def add_token(
#   authorization_guard: AuthorizationGuard = Depends(
#       get_authorization_guard),
):
    return {}

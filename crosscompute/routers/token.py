from fastapi import APIRouter


router = APIRouter()


@router.post(
    'tokens.json',
    tags=['token'])
async def add_token():
    return {}

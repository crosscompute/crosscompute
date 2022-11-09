from fastapi import APIRouter, Request

from ..constants import (
    MUTATION_ROUTE)


router = APIRouter()


@router.get(
    MUTATION_ROUTE.format(uri='{uri:.*}'),
    tags=['mutation'])
async def see_mutation(request: Request):
    return {}

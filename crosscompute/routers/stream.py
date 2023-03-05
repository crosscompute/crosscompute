import asyncio
import json

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ..constants import (
    MUTATION_ROUTE,
    STREAM_ROUTE)
from ..routines.mutation import get_mutation


router = APIRouter()


@router.get(
    STREAM_ROUTE + MUTATION_ROUTE.format(uri='{reference_uri:path}'),
    tags=['stream'])
async def see_mutation_stream(
    reference_uri: str,
    old_timestamp: float = Query(default=0, alias='t'),
):
    # TODO: Consider adding guard
    async def loop():
        reference_timestamp = old_timestamp
        while True:
            await asyncio.sleep(1)
            d = get_mutation(reference_uri, reference_timestamp)
            if d[
                'configurations'
            ] or d[
                'scripts'
            ] or d[
                'variables'
            ] or d[
                'templates'
            ] or d[
                'styles'
            ]:
                reference_timestamp = d['mutation_timestamp']
                yield {'data': json.dumps(d)}
    return EventSourceResponse(
        loop(), ping_message_factory=lambda: {'comment': ''})

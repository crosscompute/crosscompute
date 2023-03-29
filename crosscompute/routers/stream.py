import asyncio
import json

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ..constants import (
    MUTATION_ROUTE,
    STREAM_ROUTE)
from ..routines.mutation import get_mutation
from ..settings import site


router = APIRouter()


@router.get(
    STREAM_ROUTE + MUTATION_ROUTE.format(uri='{reference_uri:path}'),
    tags=['stream'])
async def see_mutation_stream(
    reference_uri: str,
    old_time: float = Query(default=0, alias='t'),
):
    # TODO: Consider adding guard
    uris = site['uris']

    async def loop():
        uris.append(reference_uri)
        reference_time = old_time
        try:
            while True:
                await asyncio.sleep(1)
                d = get_mutation(reference_uri, reference_time)
                if d['codes'] or d['variables'] or d['templates'] or d[
                        'styles']:
                    reference_time = d['mutation_time']
                    yield {'data': json.dumps(d)}
        except asyncio.CancelledError:
            uris.remove(reference_uri)

    return EventSourceResponse(
        loop(), ping_message_factory=lambda: {'comment': ''})

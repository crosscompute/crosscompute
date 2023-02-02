from time import time

from fastapi import APIRouter, Query

from ..constants import (
    MAXIMUM_MUTATION_AGE_IN_SECONDS,
    MUTATION_ROUTE)
from ..settings import (
    site,
    template_globals)


router = APIRouter()


@router.get(
    MUTATION_ROUTE.format(uri='{uri:path}'),
    tags=['mutation'])
async def see_mutation_json(
    uri: str,
    old_timestamp: float = Query(default=0, alias='t'),
):
    # TODO: Consider adding guard
    new_timestamp = time()
    changes = site['changes']
    configurations, variables, templates, styles = [], [], [], []
    for timestamp, infos in changes.copy().items():
        if new_timestamp - timestamp > MAXIMUM_MUTATION_AGE_IN_SECONDS:
            try:
                del changes[timestamp]
            except KeyError:
                pass
        if timestamp <= old_timestamp:
            continue
        for info in infos:
            code = info['code']
            if code == 'c':
                configurations.append({})
            elif code == 'v':
                if uri.startswith(info['uri']):
                    # TODO: Send value or diff if authorized
                    variables.append({'id': info['id']})
            elif code == 't':
                if uri.startswith(info['uri']):
                    templates.append({})
            elif code == 's':
                styles.append({})
    return {
        'server_timestamp': template_globals['server_timestamp'],
        'mutation_timestamp': new_timestamp,
        'configurations': configurations,
        'variables': variables,
        'templates': templates,
        'styles': styles,
    }

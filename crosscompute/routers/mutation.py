# TODO: Consider having production pages that do not change ignore mutations
from time import time

from fastapi import APIRouter, Query

from ..constants import (
    MAXIMUM_MUTATION_AGE_IN_SECONDS,
    MUTATION_ROUTE)
from ..variables import (
    site_variables,
    template_environment)


router = APIRouter()


@router.get(
    MUTATION_ROUTE.format(uri='{uri:path}'),
    tags=['mutation'])
# async def see_mutation_json(uri: str, t: float = 0):
async def see_mutation_json(
    uri: str,
    old_timestamp: float = Query(default=0, alias='t'),
):
    # TODO: Consider adding guard
    new_timestamp = time()
    infos_by_timestamp = site_variables['infos_by_timestamp']
    configurations, variables, templates, styles = [], [], [], []
    for timestamp, infos in infos_by_timestamp.copy().items():
        if new_timestamp - timestamp > MAXIMUM_MUTATION_AGE_IN_SECONDS:
            try:
                del infos_by_timestamp[timestamp]
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
        'server_timestamp': template_environment.globals['server_timestamp'],
        'mutation_timestamp': new_timestamp,
        'configurations': configurations,
        'variables': variables,
        'templates': templates,
        'styles': styles,
    }


'''
- [X] Define infos_by_timestamp in variables/site_variables
- [X] Define t:str = 0 in see_mutation
- [X] Use template_environment.globals['server_timestamp']
- [X] Remove request from see_mutation_json
- [X] Restore comment about guard
- [ ] Fix issue with mutation route not found
- [ ] Use query alias
'''

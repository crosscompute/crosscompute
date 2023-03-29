from time import time

from ..constants import (
    MAXIMUM_MUTATION_AGE_IN_SECONDS)
from ..settings import (
    site,
    template_globals)


def get_mutation(reference_uri, old_t):
    codes, variables, templates, styles = [], [], [], []
    new_t = time()
    changes = site['changes']
    for t, infos in changes.copy().items():
        if new_t - t > MAXIMUM_MUTATION_AGE_IN_SECONDS:
            try:
                del changes[t]
            except KeyError:
                pass
        if t <= old_t:
            continue
        for info in infos:
            code = info['code']
            if code == 'c':
                codes.append({})
            elif code == 'v':
                if reference_uri.startswith(info['uri']):
                    # TODO: Send value if authorized
                    variables.append({'id': info['id']})
            elif code == 't':
                if reference_uri.startswith(info['uri']):
                    templates.append({})
            elif code == 's':
                styles.append({})
    return {
        'codes': codes, 'variables': variables,
        'templates': templates, 'styles': styles,
        'mutation_timestamp': new_t,
        'server_timestamp': template_globals['server_timestamp']}

from time import time

from ..constants import (
    MAXIMUM_MUTATION_AGE_IN_SECONDS)
from ..settings import (
    site,
    template_globals)


def get_mutation(reference_uri, old_timestamp):
    codes, variables, templates, styles = [], [], [], []
    new_timestamp = time()
    changes = site['changes']
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
        'mutation_timestamp': new_timestamp,
        'server_timestamp': template_globals['server_timestamp']}

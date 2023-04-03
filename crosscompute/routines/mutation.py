from time import time

from ..constants import (
    Info,
    MAXIMUM_MUTATION_AGE_IN_SECONDS)
from ..settings import (
    template_globals)
from .uri import (
    get_step_code)


def get_mutation(file_changes, reference_uri, old_time):
    configurations, variables, templates, styles = [], [], [], []
    new_time = time()
    step_code = get_step_code(reference_uri)
    for t, infos in file_changes.copy().items():
        if new_time - t > MAXIMUM_MUTATION_AGE_IN_SECONDS:
            try:
                del file_changes[t]
            except KeyError:
                pass
        if t <= old_time:
            continue
        for info in infos:
            code = info['code']
            if code == Info.CONFIGURATION:
                configurations.append({})
            elif code == Info.VARIABLE and info['step'] != 'i':
                if reference_uri.startswith(info['uri']):
                    # TODO: Send value if authorized
                    variables.append({'id': info['id']})
            elif code == Info.TEMPLATE:
                if 'step' in info and info['step'] != step_code:
                    continue
                if reference_uri.startswith(info['uri']):
                    templates.append({})
            elif code == Info.STYLE:
                styles.append({})
    return {
        'configurations': configurations, 'variables': variables,
        'templates': templates, 'styles': styles, 'mutation_time': new_time,
        'server_time': template_globals['server_time']}

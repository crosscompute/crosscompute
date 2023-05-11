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
    variable_ids, new_time = [], time()
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
            categorize_mutation(
                info, reference_uri, step_code, variable_ids,
                configurations, variables, templates, styles)
    return {
        'configurations': configurations,
        'variables': variables,
        'templates': templates,
        'styles': styles,
        'mutation_time': new_time,
        'server_time': template_globals['server_time']}


def categorize_mutation(
        info, reference_uri, step_code, variable_ids,
        configurations, variables, templates, styles):
    match info['code']:
        case Info.CONFIGURATION:
            configurations.append({})
        case Info.VARIABLE:
            if is_irrelevant_variable(info, reference_uri, variable_ids):
                return
            # TODO: Send value if authorized
            variable_id = info['id']
            variable_ids.append(variable_id)
            variables.append({'id': variable_id})
        case Info.TEMPLATE:
            if is_irrelevant_template(info, step_code, reference_uri):
                return
            templates.append({})
        case Info.STYLE:
            styles.append({})


def is_irrelevant_variable(info, reference_uri, variable_ids):
    if info['step'] == 'i':
        return True
    if not reference_uri.startswith(info['uri']):
        return True
    if info['id'] in variable_ids:
        return True
    return False


def is_irrelevant_template(info, step_code, reference_uri):
    if info.get('step') != step_code:
        return True
    if not reference_uri.startswith(info['uri']):
        return True
    return False

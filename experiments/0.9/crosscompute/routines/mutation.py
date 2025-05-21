from time import time

from ..constants import (
    Info,
    MAXIMUM_MUTATION_AGE_IN_SECONDS)
from ..settings import (
    template_globals)
from .uri import (
    get_step_code)


def get_mutation(file_changes, reference_uri, old_time):
    variable_by_id, configurations, templates, styles = {}, [], [], []
    new_time, step_code = time(), get_step_code(reference_uri)
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
                info, reference_uri, step_code, variable_by_id,
                configurations, templates, styles)
    d = {
        'mutation_time': new_time,
        'server_time': template_globals['server_time']}
    if configurations:
        d['configurations'] = configurations
    if variable_by_id:
        d['variables'] = list(variable_by_id.values())
    if templates:
        d['templates'] = templates
    if styles:
        d['styles'] = styles
    return d


def categorize_mutation(
        info, reference_uri, step_code, variable_by_id,
        configurations, templates, styles):
    match info['code']:
        case Info.CONFIGURATION:
            configurations.append({})
        case Info.VARIABLE:
            if is_irrelevant_variable(info, reference_uri):
                return
            variable_id = info['id']
            d = {'i': variable_id}
            if 'value' in info:
                d['v'] = info['value']
            if 'configuration' in info:
                d['c'] = info['configuration']
            variable_by_id[variable_id] = variable_by_id.get(
                variable_id, {}) | d
        case Info.TEMPLATE:
            if is_irrelevant_template(info, step_code, reference_uri):
                return
            templates.append({})
        case Info.STYLE:
            styles.append({})


def is_irrelevant_variable(info, reference_uri):
    if info['step'] == 'i':
        return True
    if not reference_uri.startswith(info['uri']):
        return True
    return False


def is_irrelevant_template(info, step_code, reference_uri):
    if info.get('step') != step_code:
        return True
    if not reference_uri.startswith(info['uri']):
        return True
    return False

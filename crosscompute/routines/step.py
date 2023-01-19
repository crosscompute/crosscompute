from logging import getLogger

from ..constants import (
    STEP_CODE_BY_NAME,
    STEP_ROUTE)
from ..macros.iterable import find_item
from .variable import Element, VariableView


def get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name):
    automation_uri = automation_definition.uri
    batch_uri = batch_definition.uri
    step_code = STEP_CODE_BY_NAME[step_name]
    step_uri = STEP_ROUTE.format(step_code=step_code)
    return automation_uri + batch_uri + step_uri


def render_variable_html(
        match, variable_definitions, batch, m, i, root_uri, request_params,
        step_name, design_name, for_print):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'root_uri':
        return root_uri
    terms = matching_inner_text.split('|')
    variable_id = terms[0].strip()
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id)
    except StopIteration:
        L.warning(
            '%s variable in template but not in configuration', variable_id)
        matching_outer_text = match.group(0)
        return matching_outer_text
    view = VariableView.get_from(variable_definition)
    mode_name = variable_definition.get('mode', step_name)
    element = Element(
        f'v{next(i)}', root_uri, request_params, mode_name, design_name,
        for_print, terms[1:])
    page_dictionary = view.render(batch, element)
    for k, v in m.items():
        v.extend(_.strip() for _ in page_dictionary[k])
    return page_dictionary['main_text']


L = getLogger(__name__)

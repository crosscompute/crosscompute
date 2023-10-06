from itertools import count

from ..constants import (
    MUTATION_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
from ..macros.iterable import find_item
from .batch import DiskBatch
from .variable import VariableView


def get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name):
    automation_uri = automation_definition.uri
    batch_uri = batch_definition.uri
    step_code = STEP_CODE_BY_NAME[step_name]
    step_uri = STEP_ROUTE.format(step_code=step_code)
    return automation_uri + batch_uri + step_uri


def get_automation_response_dictionary(
        automation_definition, root_uri, request_params):
    automation_uri = automation_definition.uri
    step_name = automation_definition.get_design_name('automation')
    if step_name == 'none':
        layout_settings = get_layout_settings(step_name, request_params)
        d = {
            'css_uris': automation_definition.css_uris,
            'css_texts': get_css_texts(layout_settings),
            'is_done': 1,
            'mutation_uri': MUTATION_ROUTE.format(uri=automation_uri)}
    else:
        layout_settings = get_layout_settings(
            automation_definition.get_design_name(step_name), request_params)
        # TODO: Let creator choose which batch to feature by default
        batch = DiskBatch(
            automation_definition, automation_definition.batch_definitions[0])
        d = get_step_response_dictionary(
            batch, step_name, root_uri, layout_settings, request_params)
    return {
        'copyright_name': automation_definition.copyright_name,
        'copyright_uri': automation_definition.copyright_uri,
        'attribution_text': automation_definition.attribution_text,
        'name': automation_definition.name,
        'uri': automation_uri,
        'step_name': step_name,
    } | d


def get_step_response_dictionary(
        batch, step_name, root_uri, layout_settings, request_params):
    automation_definition = batch.automation_definition
    variable_definitions = automation_definition.get_variable_definitions(
        step_name, with_all=True)
    render_html = partial(
        render_variable_html,
        step_name=step_name,
        variable_definitions=variable_definitions,
        button_text_by_id=automation_definition.button_text_by_id,
        root_uri=root_uri)
    main_text, template_count = get_main_pack(
        automation_definition, step_name, root_uri, render_html,
        layout_settings)
    mutation_reference_uri = get_automation_batch_step_uri(
        automation_definition, batch.definition, step_name)
    return layout_settings | {
        'is_done': batch.is_done(),
        'has_interval': automation_definition.interval_timedelta is not None,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri)}


def get_main_pack(
        automation_definition, step_name, root_uri, render_html,
        layout_settings):
    '''
    template_definitions = automation_definition.get_template_definitions(
        step_name)
    '''
    template_definitions = (
        automation_definition.template_definitions_by_step_name[step_name])
    template_count = len(template_definitions)
    format_html = partial(
        format_template_html,
        root_uri=root_uri,
        render_html=render_html,
        with_button_panel=get_with_button_panel(
            layout_settings, step_name, template_count),
        button_text_by_id=automation_definition.button_text_by_id)
    if not template_count:
        template_text = make_template_text(automation_definition, step_name)
        return format_html(
            template_text, template_index=0, template_expression=''), 1
    parts = []
    automation_folder = automation_definition.folder
    for template_index, template_definition in enumerate(template_definitions):
        # TODO: replace with an abstraction that relies on AutomationDefinition
        path = automation_folder / template_definition.path
        try:
            with path.open('rt') as f:
                text = f.read().strip()
        except IOError:
            L.error('template path "%s" was not found', path)
            continue
        parts.append(format_html(
            text, template_index, template_definition.expression))
    return '\n'.join(parts), template_count


def make_template_text(automation_definition, step_name):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    variable_ids = (_.id for _ in variable_definitions)
    return ' '.join('{%s}' % _ for _ in variable_ids)

from functools import partial
from html.parser import HTMLParser
from itertools import count
from logging import getLogger

from invisibleroads_macros_web.markdown import (
    get_html_from_markdown,
    remove_parent_paragraphs)

from ..constants import (
    BUTTON_TEXT_BY_ID,
    MUTATION_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VARIABLE_ID_WHITELIST_PATTERN)
from ..macros.iterable import find_item
from .asset import asset_storage
from .batch import DiskBatch
from .configuration import AutomationDefinition
from .variable import Element, VariableView


class TemplateFilter(HTMLParser):

    def __init__(self, root_uri, render_html, template_index, *args, **kwargs):
        self.render_text = partial(render_text, root_uri=root_uri)
        self.render_html = partial(render_html, template_index=template_index)
        self.in_script = False
        self.template_parts = []
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = True
        attribute_strings = []
        for k, v in attrs:
            v = VARIABLE_ID_WHITELIST_PATTERN.sub(self.render_text, v)
            attribute_strings.append(f'{k}="{v}"')
        attributes_string = ' ' + ' '.join(
            attribute_strings) if attribute_strings else ''
        self.template_parts.append(f'<{tag}{attributes_string}>')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        self.template_parts.append(f'</{tag}>')

    def handle_data(self, data):
        in_script = self.in_script
        if in_script:
            data = VARIABLE_ID_WHITELIST_PATTERN.sub(self.render_text, data)
        else:
            data = VARIABLE_ID_TEMPLATE_PATTERN.sub(self.render_html, data)
        self.template_parts.append(data)

    def process(self, text):
        self.template_parts = []
        self.feed(text)
        return ''.join(self.template_parts)


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
        d = get_step_response_dictionary(
            automation_definition, automation_definition.batch_definitions[0],
            step_name, root_uri, layout_settings, request_params)
    return {
        'copyright_name': automation_definition.copyright_name,
        'copyright_uri': automation_definition.copyright_uri,
        'attribution_text': automation_definition.attribution_text,
        'name': automation_definition.name,
        'uri': automation_uri,
        'step_name': step_name,
    } | d


def get_step_response_dictionary(
        automation_definition, batch_definition, step_name, root_uri,
        layout_settings, request_params):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name, with_all=True)
    batch = DiskBatch(automation_definition, batch_definition)
    m = {
        'css_uris': automation_definition.css_uris.copy(), 'css_texts': [],
        'js_uris': [], 'js_texts': []}
    render_html = partial(
        render_variable_html, batch=batch, step_name=step_name,
        variable_definitions=variable_definitions, variable_index=count(),
        button_text_by_id=automation_definition.button_text_by_id,
        root_uri=root_uri, layout_settings=layout_settings,
        request_params=request_params, m=m)
    main_text, template_count = get_main_pack(
        automation_definition, step_name, root_uri, render_html,
        layout_settings)
    mutation_reference_uri = get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    return layout_settings | {
        'css_uris': m['css_uris'],
        'css_texts': get_css_texts(layout_settings) + m['css_texts'],
        'js_uris': m['js_uris'],
        'js_texts': m['js_texts'],
        'main_text': main_text, 'template_count': template_count,
        'is_done': batch.is_done(),
        'has_interval': automation_definition.interval_timedelta is not None,
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri)}


def render_text(match, root_uri):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'ROOT_URI':
        return root_uri
    matching_outer_text = match.group(0)
    return matching_outer_text


def render_variable_html(
        match, batch, step_name, variable_definitions, variable_index,
        template_index, button_text_by_id, root_uri, layout_settings,
        request_params, m):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'ROOT_URI':
        return root_uri
    elif matching_inner_text == 'BUTTON_PANEL':
        return get_button_panel_html(template_index, button_text_by_id)
    terms = matching_inner_text.split('|')
    variable_id = terms[0].strip()
    try:
        variable_definition = find_item(
            variable_definitions, 'id', variable_id)
    except StopIteration:
        L.warning(
            'variable "%s" is in the template but is missing from the '
            'configuration',
            variable_id)
        matching_outer_text = match.group(0)
        return matching_outer_text
    view = VariableView.get_from(variable_definition)
    mode_name = variable_definition.get('mode', step_name)
    element = Element(
        f'v{next(variable_index)}', mode_name, request_params,
        layout_settings, terms[1:])
    page_dictionary = view.render(batch, element)
    for k, v in m.items():
        v.extend(_.strip() for _ in page_dictionary[k])
    return page_dictionary['main_text']


def get_main_pack(
        a: AutomationDefinition, step_name, root_uri, render_html,
        layout_settings):
    template_definitions = a.template_definitions_by_step_name[step_name]
    template_count = len(template_definitions)
    format_html = partial(
        format_template_html,
        root_uri=root_uri,
        render_html=render_html,
        with_button_panel=get_with_button_panel(
            layout_settings, step_name, template_count),
        button_text_by_id=a.button_text_by_id)
    if not template_count:
        template_text = make_template_text(a, step_name)
        return format_html(
            template_text, template_index=0, template_expression=''), 1
    parts = []
    automation_folder = a.folder
    for template_index, template_definition in enumerate(template_definitions):
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


def get_button_panel_html(template_index, button_text_by_id):
    return BUTTON_PANEL_HTML.render({
        'template_index': template_index,
        'button_text_by_id': BUTTON_TEXT_BY_ID | button_text_by_id})


def get_layout_settings(design_name, request_params):
    return {
        'design_name': design_name,
        'for_embed': '_embed' in request_params,
        'for_print': '_print' in request_params}


def get_css_texts(layout_settings):
    css_texts = []
    if layout_settings['for_embed']:
        css_texts.append(EMBEDDED_CSS)
    else:
        css_texts.append(DEFAULT_CSS)
    if layout_settings['design_name'] == 'flex':
        css_texts.append(FLEX_CSS)
    return css_texts


def get_with_button_panel(layout_settings, step_name, template_count):
    if layout_settings['design_name'] == 'none':
        return False
    if layout_settings['for_print']:
        return False
    if step_name != 'input' and template_count <= 1:
        return False
    return True


def make_template_text(automation_definition, step_name):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name)
    variable_ids = (_.id for _ in variable_definitions)
    return ' '.join('{%s}' % _ for _ in variable_ids)


def format_template_html(
        text, template_index, template_expression, root_uri, render_html,
        with_button_panel, button_text_by_id):
    l_ = ' _live' if not template_index and not template_expression else ''
    x_ = (
        f' data-expression="{template_expression}"'
        if template_expression else '')
    h = get_html_from_markdown(text)
    h = TemplateFilter(
        root_uri, render_html, template_index=template_index).process(h)
    h = remove_parent_paragraphs(h)
    if with_button_panel and 'class="_continue"' not in h:
        h += '\n' + get_button_panel_html(template_index, button_text_by_id)
    return (
        f'<div id="_t{template_index}" class="_template{l_}"{x_}>'
        f'\n{h}\n</div>')


L = getLogger(__name__)


EMBEDDED_CSS = asset_storage.load_raw_text('embedded.css')
DEFAULT_CSS = asset_storage.load_raw_text('default.css')
FLEX_CSS = asset_storage.load_raw_text('flex.css')
BUTTON_PANEL_HTML = asset_storage.load_jinja_text('button-panel.html')

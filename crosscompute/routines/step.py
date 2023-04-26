from functools import partial
from html.parser import HTMLParser
from itertools import count
from logging import getLogger

from invisibleroads_macros_web.markdown import get_html_from_markdown

from ..constants import (
    MUTATION_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VARIABLE_ID_WHITELIST_PATTERN)
from ..macros.iterable import find_item, get_unique_order
from ..settings import button_text_by_id, template_globals
from .asset import asset_storage
from .batch import DiskBatch
from .variable import Element, VariableView


class TemplateFilter(HTMLParser):

    def __init__(self, render_html, template_index, *args, **kwargs):
        self.render_html = partial(render_html, template_index=template_index)
        self.in_script = False
        self.template_parts = []
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = True
        attribute_strings = [f'{k}="{v}"' for k, v in attrs]
        attributes_string = ' ' + ' '.join(
            attribute_strings) if attribute_strings else ''
        self.template_parts.append(f'<{tag}{attributes_string}>')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        self.template_parts.append(f'</{tag}>')

    def handle_data(self, data):
        in_script = self.in_script
        render_html = self.render_html
        if in_script:
            data = VARIABLE_ID_WHITELIST_PATTERN.sub(render_html, data)
        else:
            data = VARIABLE_ID_TEMPLATE_PATTERN.sub(render_html, data)
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


def get_step_response_dictionary(
        automation_definition, batch_definition, step_name, request_params):
    variable_definitions = automation_definition.get_variable_definitions(
        step_name, with_all=True)
    batch = DiskBatch(automation_definition, batch_definition)
    m = {
        'css_uris': automation_definition.css_uris.copy(), 'css_texts': [],
        'js_uris': [], 'js_texts': []}
    design_name = automation_definition.get_design_name(step_name)
    for_embed = '_embed' in request_params
    for_print = '_print' in request_params
    render_html = partial(
        render_variable_html, variable_definitions=variable_definitions,
        batch=batch, m=m, variable_index=count(),
        root_uri=template_globals['root_uri'], request_params=request_params,
        step_name=step_name, design_name=design_name, for_print=for_print)
    main_text, template_count = get_main_pack(
        automation_definition, step_name, render_html)
    mutation_reference_uri = get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    return {
        'css_uris': get_unique_order(m['css_uris']),
        'css_text': get_css_text(design_name, for_embed, for_print, m),
        'main_text': main_text, 'template_count': template_count,
        'js_uris': get_unique_order(m['js_uris']),
        'js_text': '\n'.join(get_unique_order(m['js_texts'])),
        'for_embed': for_embed, 'for_print': for_print,
        'has_interval': automation_definition.interval_timedelta is not None,
        'is_done': batch.is_done(),
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri)}


def render_variable_html(
        match, variable_definitions, batch, m, variable_index, template_index,
        root_uri, request_params, step_name, design_name, for_print):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'ROOT_URI':
        return root_uri
    elif matching_inner_text == 'BUTTON_PANEL':
        return BUTTON_PANEL_HTML.render({
            'template_index': template_index,
            'button_text_by_id': button_text_by_id})
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
        f'v{next(variable_index)}', request_params, mode_name, design_name,
        for_print, terms[1:])
    page_dictionary = view.render(batch, element)
    for k, v in m.items():
        v.extend(_.strip() for _ in page_dictionary[k])
    return page_dictionary['main_text']


def get_css_text(design_name, for_embed, for_print, m):
    css_texts = []
    if for_embed:
        css_texts.append(EMBEDDED_CSS)
    elif for_print:
        css_texts.append(PRINTED_CSS)
    else:
        css_texts.append(DEFAULT_CSS)
    if design_name == 'flex':
        css_texts.append(FLEX_CSS)
    return '\n'.join(css_texts + get_unique_order(m['css_texts']))


def get_main_pack(automation_definition, step_name, render_html):
    a = automation_definition
    template_definitions = a.template_definitions_by_step_name[step_name]
    with_button_panel = step_name == 'input' or len(template_definitions) > 1

    def format_template(text, i=0, x=''):
        l_ = ' _live' if not i and not x else ''
        x_ = f' data-expression="{x}"' if x else ''
        g = TemplateFilter(render_html, template_index=i).process(text)
        h = get_html_from_markdown(g)
        if with_button_panel and 'class="_continue"' not in h:
            h += '\n' + BUTTON_PANEL_HTML.render({
                'template_index': i,
                'button_text_by_id': button_text_by_id})
        return f'<div id="_t{i}" class="_template{l_}"{x_}>\n{h}\n</div>'

    if not template_definitions:
        variable_definitions = a.get_variable_definitions(step_name)
        variable_ids = (_.id for _ in variable_definitions)
        text = '\n'.join('{%s}' % _ for _ in variable_ids)
        return format_template(text), 1
    parts = []
    automation_folder = a.folder
    for i, template_definition in enumerate(template_definitions):
        path = automation_folder / template_definition.path
        with path.open('rt') as f:
            text = f.read().strip()
        parts.append(format_template(text, i, template_definition.expression))
    return '\n'.join(parts), len(template_definitions)


L = getLogger(__name__)


EMBEDDED_CSS = asset_storage.load_raw_text('embedded.css')
PRINTED_CSS = asset_storage.load_raw_text('printed.css')
DEFAULT_CSS = asset_storage.load_raw_text('default.css')
FLEX_CSS = asset_storage.load_raw_text('flex.css')
BUTTON_PANEL_HTML = asset_storage.load_jinja_text('button-panel.html')

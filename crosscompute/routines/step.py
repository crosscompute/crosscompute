from functools import partial
from html.parser import HTMLParser
from itertools import count
from logging import getLogger

from invisibleroads_macros_web.markdown import get_html_from_markdown

from ..constants import (
    MUTATION_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN)
from ..macros.iterable import find_item, get_unique_order
from ..settings import template_globals
from .asset import asset_storage
from .batch import DiskBatch
from .variable import Element, VariableView


class VariableParser(HTMLParser):

    def __init__(self, render_html, *args, **kwargs):
        self.render_html = render_html
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
        if not self.in_script:
            data = VARIABLE_ID_TEMPLATE_PATTERN.sub(self.render_html, data)
        self.template_parts.append(data)

    def parse_text(self, text):
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
    css_uris = automation_definition.css_uris
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    design_name = automation_definition.get_design_name(step_name)
    for_embed = '_embed' in request_params
    for_print = '_print' in request_params
    render_element_html = partial(
        render_variable_html, variable_definitions=variable_definitions,
        batch=batch, m=m, i=count(), root_uri=template_globals['root_uri'],
        request_params=request_params, step_name=step_name,
        design_name=design_name, for_print=for_print)
    template_text = automation_definition.get_template_text(step_name)
    main_text = get_html_from_markdown(VariableParser(
        render_element_html).parse_text(template_text))
    mutation_reference_uri = get_automation_batch_step_uri(
        automation_definition, batch_definition, step_name)
    return {
        'css_uris': get_unique_order(m['css_uris']),
        'css_text': get_css_text(design_name, for_embed, for_print),
        'main_text': main_text,
        'main_class': get_main_class(design_name),
        'js_uris': get_unique_order(m['js_uris']),
        'js_text': '\n'.join(get_unique_order(m['js_texts'])),
        'for_embed': for_embed,
        'for_print': for_print,
        'is_done': batch.is_done(),
        'mutation_uri': MUTATION_ROUTE.format(uri=mutation_reference_uri)}


def render_variable_html(
        match, variable_definitions, batch, m, i, root_uri, request_params,
        step_name, design_name, for_print):
    matching_inner_text = match.group(1)
    if matching_inner_text == 'ROOT_URI':
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
        f'v{next(i)}', request_params, mode_name, design_name, for_print,
        terms[1:])
    page_dictionary = view.render(batch, element)
    for k, v in m.items():
        v.extend(_.strip() for _ in page_dictionary[k])
    return page_dictionary['main_text']


def get_css_text(design_name, for_embed, for_print):
    css_texts = []
    if not for_embed and not for_print:
        css_texts.append(DEFAULT_CSS)
    elif for_embed:
        css_texts.append(EMBEDDED_CSS)
    if design_name == 'flex-vertical':
        css_texts.append(FLEX_VERTICAL_CSS)
    return '\n'.join(css_texts)


def get_main_class(design_name):
    match design_name:
        case 'flex-vertical':
            main_class = '_vertical'
        case _:
            main_class = ''
    return main_class


L = getLogger(__name__)


DEFAULT_CSS = asset_storage.load_raw_text('default.css')
EMBEDDED_CSS = asset_storage.load_raw_text('embedded.css')
FLEX_VERTICAL_CSS = asset_storage.load_raw_text('flex-vertical.css')

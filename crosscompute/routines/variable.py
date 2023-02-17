# TODO: Validate variable view configurations
import csv
import json
import shutil
from dataclasses import dataclass
from logging import getLogger
from urllib.request import urlretrieve as download_uri

from importlib_metadata import entry_points
from invisibleroads_macros_log import format_path
from invisibleroads_macros_text import format_name, format_slug
from invisibleroads_macros_web.escape import (
    escape_quotes_html,
    escape_quotes_js)

from ..constants import (
    CACHED_FILE_SIZE_LIMIT_IN_BYTES,
    MAXIMUM_FILE_CACHE_LENGTH,
    VARIABLE_ID_TEMPLATE_PATTERN,
    VIEW_BY_NAME)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationNotImplementedError,
    CrossComputeDataError)
from ..macros.disk import FileCache
from ..macros.iterable import find_item
from ..macros.package import import_attribute
from .asset import asset_storage
from .interface import Batch


@dataclass(repr=False, eq=False, order=False, frozen=True)
class Element():

    id: str
    request_params: str
    mode_name: str
    design_name: str
    for_print: bool
    function_names: list[str]


class VariableView():

    view_name = 'variable'
    environment_variable_definitions = []

    def __init__(self, variable_definition):
        self.variable_definition = variable_definition
        self.variable_id = variable_definition.id
        self.variable_path = variable_definition.path

    @classmethod
    def get_from(Class, variable_definition):
        view_name = variable_definition.view_name
        try:
            View = VIEW_BY_NAME[view_name]
        except KeyError:
            L.error('%s view not installed', view_name)
            View = Class
        return View(variable_definition)

    def parse(self, data):
        return data

    def process(self, path):
        pass

    def render(self, b: Batch, x: Element):
        if x.mode_name == 'input':
            render = self.render_input
        else:
            render = self.render_output
        page_dictionary = render(b, x)
        main_text = page_dictionary['main_text']
        if x.design_name != 'none':
            if main_text.endswith('</a>') or main_text.endswith('</span>'):
                tag_name = 'span'
            else:
                tag_name = 'div'
            page_dictionary['main_text'] = '<%s class="_view">%s</%s>' % (
                tag_name, main_text, tag_name)
        return page_dictionary

    def render_input(self, b: Batch, x: Element):
        return {
            'css_uris': [],
            'js_uris': [],
            'main_text': '',
            'js_texts': [],
        }

    def render_output(self, b: Batch, x: Element):
        return {
            'css_uris': [],
            'js_uris': [],
            'main_text': '',
            'js_texts': [],
        }


class LinkView(VariableView):

    view_name = 'link'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        file_name = c.get('file-name', self.variable_path.name)
        link_text = c.get('link-text', file_name)
        main_text = (
            f'<a id="{element_id}" href="{data_uri}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'download="{escape_quotes_html(file_name)}">'
            f'{link_text}</a>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            LINK_JS_HEADER,
            LINK_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'link_text': escape_quotes_js(link_text),
            }),
        ]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class StringView(VariableView):

    view_name = 'string'
    input_type = 'text'
    function_by_name = {
        'title': str.title,
    }

    def get_value(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        data = b.load_data_from(x.request_params, variable_definition)
        if 'value' in data:
            value = data['value']
        elif 'path' in data:
            value = load_file_text(data['path'])
        else:
            value = ''
        return value

    def render_input(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        view_name = self.view_name
        element_id = x.id
        value = self.get_value(b, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = STRING_HTML_INPUT.render({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'value': escape_quotes_html(value),
            'input_type': self.input_type,
            'suggestions': c.get('suggestions', []),
        })
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            STRING_JS_INPUT.substitute({'view_name': view_name}),
        ]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}

    def render_output(self, b: Batch, x: Element):
        value = self.get_value(b, x)
        try:
            value = apply_functions(
                value, x.function_names, self.function_by_name)
        except KeyError as e:
            L.error('%s function not supported for %s', e, self.view_name)
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = (
            f'<span id="{x.id}" '
            f'class="_{x.mode_name} _{self.view_name} {self.variable_id}">'
            f'{value}</span>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            STRING_JS_HEADER,
            STRING_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class NumberView(StringView):

    view_name = 'number'
    input_type = 'number'

    def parse(self, value):
        try:
            value = float(value)
        except ValueError:
            raise CrossComputeDataError(f'{value} is not a number')
        if value.is_integer():
            value = int(value)
        return value


class PasswordView(StringView):

    view_name = 'password'
    input_type = 'password'


class EmailView(StringView):

    view_name = 'email'
    input_type = 'email'


class TextView(VariableView):

    view_name = 'text'

    def render_input(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        data = get_data_from(x.request_params, variable_definition)
        value = data.get('value', '')
        variable_id = self.variable_id
        view_name = self.view_name
        element_id = x.id
        c = b.get_variable_configuration(variable_definition)
        main_text = TEXT_HTML_INPUT.substitute({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'attribute_string': '' if value else ' disabled',
            'value': value})
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            STRING_JS_HEADER,
            STRING_JS_INPUT.substitute({'view_name': view_name})]
        if not value:
            js_texts.extend([
                TEXT_JS_HEADER,
                TEXT_JS_INPUT.substitute({
                    'element_id': element_id,
                    'data_uri': b.get_data_uri(variable_definition, x)})])
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = (
            f'<span id="{x.id}" '
            f'class="_{x.mode_name} _{self.view_name} {self.variable_id}">'
            '</span>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            STRING_JS_HEADER,
            TEXT_JS_HEADER,
            TEXT_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class MarkdownView(TextView):

    view_name = 'markdown'
    js_uris = [
        'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
    ]

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = (
            f'<span id="{x.id}" '
            f'class="_{x.mode_name} _{self.view_name} {self.variable_id}">'
            '</span>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            STRING_JS_HEADER,
            MARKDOWN_JS_HEADER,
            MARKDOWN_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': self.js_uris, 'main_text': main_text,
            'js_texts': js_texts}


class ImageView(VariableView):

    view_name = 'image'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = (
            f'<img id="{x.id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'src="{data_uri}" alt="">')
        # TODO: Show spinner on error
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            IMAGE_JS_HEADER,
            IMAGE_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class RadioView(VariableView):

    view_name = 'radio'

    def render_input(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        view_name = self.view_name
        element_id = x.id
        c = b.get_variable_configuration(variable_definition)
        data = b.load_data_from(x.request_params, variable_definition)
        value = data.get('value', '')
        main_text = RADIO_HTML_INPUT.render({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'options': get_configuration_options(c, [value]),
            'value': value})
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            RADIO_JS_INPUT.substitute({'view_name': view_name})]
        if variable_definition.step_name != 'input':
            data_uri = b.get_data_uri(variable_definition, x)
            js_texts.extend([
                RADIO_JS_HEADER,
                RADIO_JS_OUTPUT.substitute({
                    'variable_id': variable_id, 'element_id': element_id,
                    'data_uri': data_uri})])
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class CheckboxView(VariableView):

    view_name = 'checkbox'

    def render_input(self, b: Batch, x: Element):
        element_id = x.id
        view_name = self.view_name
        variable_id = self.variable_id
        variable_definition = self.variable_definition
        c = b.get_variable_configuration(variable_definition)
        data = b.load_data_from(x.request_params, variable_definition)
        values = data.get('value', '').splitlines()
        main_text = CHECKBOX_HTML_INPUT.render({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'options': get_configuration_options(c, values),
            'values': values})
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            CHECKBOX_JS_INPUT.substitute({'view_name': view_name})]
        if variable_definition.step_name != 'input':
            data_uri = b.get_data_uri(variable_definition, x)
            js_texts.extend([
                CHECKBOX_JS_HEADER,
                CHECKBOX_JS_OUTPUT.substitute({
                    'variable_id': variable_id,
                    'element_id': element_id,
                    'data_uri': data_uri})])
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class TableView(VariableView):

    view_name = 'table'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        main_text = (
            f'<table id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}">'
            '<thead/><tbody/></table>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)
        js_texts = [
            TABLE_JS_HEADER,
            TABLE_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class FrameView(VariableView):

    view_name = 'frame'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_variable_configuration(variable_definition)
        data = b.load_data(variable_definition)
        if 'value' in data:
            value = data['value']
        else:
            value = ''
        main_text = (
            f'<iframe id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'src="{escape_quotes_html(value)}" frameborder="0">'
            '</iframe>')
        if x.design_name not in ['none']:
            main_text = add_label_html(main_text, c, variable_id, element_id)

        js_texts = [
            FRAME_JS_HEADER,
            FRAME_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': main_text,
            'js_texts': js_texts}


class JsonView(VariableView):

    view_name = 'json'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        js_texts = [
            JSON_JS_HEADER,
            JSON_JS_OUTPUT.substitute({
                'variable_id': variable_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'js_uris': [], 'main_text': '',
            'js_texts': js_texts}


def initialize_view_by_name():
    for entry_point in entry_points().select(group='crosscompute.views'):
        VIEW_BY_NAME[entry_point.name] = import_attribute(entry_point.value)
    return VIEW_BY_NAME


def save_variable_data(target_path, data_by_id, variable_definitions):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id)
    if target_path.suffix == '.dictionary':
        with open(target_path, 'wt') as input_file:
            variable_value_by_id = get_variable_value_by_id(
                variable_data_by_id)
            json.dump(variable_value_by_id, input_file)
    elif len(variable_data_by_id) > 1:
        raise CrossComputeConfigurationError(
            'use file extension .dictionary for multiple variables')
    else:
        variable_id, variable_data = list(variable_data_by_id.items())[0]
        if 'value' in variable_data:
            open(target_path, 'wt').write(variable_data['value'])
        elif 'path' in variable_data:
            shutil.copy(variable_data['path'], target_path)
        elif 'uri' in variable_data:
            download_uri(variable_data['uri'], target_path)
        variable_definition = find_item(
            variable_definitions, 'id', variable_id)
        variable_view = VariableView.get_from(variable_definition)
        variable_view.process(target_path)


def get_data_by_id_from_folder(folder, variable_definitions):
    data_by_id = {}
    for variable_definition in variable_definitions:
        variable_id = variable_definition.id
        variable_path = variable_definition.path
        variable_data = load_variable_data(folder / variable_path, variable_id)
        data_by_id[variable_id] = variable_data
    return data_by_id


def yield_data_by_id_from_csv(path, variable_definitions):
    try:
        with path.open('rt') as f:
            csv_reader = csv.reader(f)
            keys = [_.strip() for _ in next(csv_reader)]
            for values in csv_reader:
                data_by_id = {k: {'value': v} for k, v in zip(keys, values)}
                data_by_id = parse_data_by_id(data_by_id, variable_definitions)
                if data_by_id.get('#') == '#':
                    continue
                yield data_by_id
    except OSError as e:
        raise CrossComputeConfigurationError(e)
    except StopIteration:
        pass


def yield_data_by_id_from_txt(path, variable_definitions):
    if len(variable_definitions) > 1:
        raise CrossComputeConfigurationError(
            'use .csv to configure multiple variables')

    try:
        variable_id = variable_definitions[0].id
    except IndexError:
        variable_id = None

    try:
        with path.open('rt') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                data_by_id = {variable_id: {'value': line}}
                yield parse_data_by_id(data_by_id, variable_definitions)
    except OSError as e:
        raise CrossComputeConfigurationError(e)


def get_data_from(request_params, variable_definition):
    variable_id = variable_definition.id
    if variable_id in request_params:
        data = {'value': request_params[variable_id]}
    else:
        data = {}
    return data


def parse_data_by_id(data_by_id, variable_definitions):
    for variable_definition in variable_definitions:
        variable_id = variable_definition.id
        try:
            variable_data = data_by_id[variable_id]
        except KeyError:
            continue
        if 'value' not in variable_data:
            continue
        variable_value = variable_data['value']
        variable_view = VariableView.get_from(variable_definition)
        try:
            variable_value = variable_view.parse(variable_value)
        except CrossComputeDataError as e:
            raise CrossComputeDataError(f'{e} for variable {variable_id}')
        variable_data['value'] = variable_value
    return data_by_id


def update_variable_data(path, data_by_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.suffix == '.dictionary':
            if path.exists():
                with path.open('r+t') as f:
                    d = json.load(f)
                    d.update(data_by_id)
                    f.seek(0)
                    json.dump(d, f)
                    f.truncate()
            else:
                with path.open('wt') as f:
                    d = data_by_id
                    json.dump(d, f)
        else:
            with path.open('wt') as f:
                f.write(data_by_id.values()[0])
    except (json.JSONDecodeError, OSError) as e:
        raise CrossComputeDataError(e)


def remove_variable_data(path, variable_ids):
    if not path.exists():
        return
    try:
        if path.suffix == '.dictionary':
            with path.open('r+t') as f:
                d = json.load(f)
                for variable_id in variable_ids:
                    del d[variable_id]
                f.seek(0)
                json.dump(d, f)
                f.truncate()
        else:
            path.unlink(missing_ok=True)
    except (json.JSONDecodeError, OSError) as e:
        raise CrossComputeDataError(e)


def process_variable_data(path, variable_definition):
    variable_id = variable_definition.id
    variable_view = VariableView.get_from(variable_definition)
    variable_data = load_variable_data(path, variable_id)
    variable_view.process(path)
    return variable_data


def load_variable_data(path, variable_id):
    file_data = FILE_DATA_CACHE[path]
    if path.suffix == '.dictionary':
        file_value = file_data['value']
        try:
            variable_value = file_value[variable_id]
        except KeyError:
            raise CrossComputeDataError(
                f'variable {variable_id} not found in {format_path(path)}')
        variable_data = {'value': variable_value}
    else:
        variable_data = file_data
    return variable_data


def load_file_data(path):
    if not path.exists():
        raise CrossComputeDataError(f'could not find {format_path(path)}')
    suffix = path.suffix
    if suffix == '.dictionary':
        return load_dictionary_data(path)
    if suffix == '.txt':
        return load_text_data(path)
    return {'path': path}


def load_dictionary_data(path):
    try:
        value = json.load(path.open('rt'))
    except (json.JSONDecodeError, OSError) as e:
        raise CrossComputeDataError(
            f'could not load {format_path(path)}: {e}')
    if not isinstance(value, dict):
        raise CrossComputeDataError(
            f'expected dictionary in {format_path(path)}')
    return {'value': value}


def load_text_data(path):
    try:
        if path.stat().st_size > CACHED_FILE_SIZE_LIMIT_IN_BYTES:
            return {'path': path}
        value = load_file_text(path)
    except OSError as e:
        raise CrossComputeDataError(
            f'could not load {format_path(path)}: {e}')
    return {'value': value}


def load_file_text(path):
    return path.read_text().rstrip()


def get_variable_data_by_id(
        variable_definitions, data_by_id, with_exceptions=True):
    variable_data_by_id = {}
    for variable_definition in variable_definitions:
        variable_id = variable_definition.id
        if None in data_by_id:
            variable_data = data_by_id[None]
        else:
            try:
                variable_data = data_by_id[variable_id]
            except KeyError:
                if not with_exceptions:
                    continue
                raise CrossComputeConfigurationError(
                    f'{variable_id} not defined in batch configuration')
        variable_data_by_id[variable_id] = variable_data
    return variable_data_by_id


def get_variable_value_by_id(data_by_id):
    return {
        variable_id: data['value'] for variable_id, data in data_by_id.items()
    }


def format_text(text, data_by_id):
    text = str(text)
    if not data_by_id:
        return text

    def f(match):
        expression_text = match.group(1)
        expression_terms = expression_text.split('|')
        variable_id = expression_terms[0].strip()
        try:
            variable_data = data_by_id[variable_id]
        except KeyError:
            raise CrossComputeConfigurationError(
                f'variable {variable_id} missing in batch configuration')
        value = variable_data.get('value', '')
        try:
            value = apply_functions(value, expression_terms[1:], {
                'slug': format_slug,
                'title': str.title})
        except KeyError as e:
            raise CrossComputeConfigurationNotImplementedError(
                f'{e} function not supported in "{text}"')
        return str(value)

    return VARIABLE_ID_TEMPLATE_PATTERN.sub(f, text)


def apply_functions(value, function_names, function_by_name):
    for function_name in function_names:
        function_name = function_name.strip()
        if not function_name:
            continue
        try:
            f = function_by_name[function_name]
        except KeyError:
            raise
        value = f(value)
    return value


def add_label_html(main_text, variable_configuration, variable_id, element_id):
    label_text = get_label_text(variable_configuration, variable_id)
    if label_text:
        main_text = '<label for="%s">%s</label> %s' % (
            element_id, label_text, main_text)
    return main_text


def get_label_text(variable_configuration, variable_id):
    if 'label' in variable_configuration:
        label_text = variable_configuration['label'] or ''
    else:
        label_text = format_name(variable_id)
    return label_text.strip()


def get_configuration_options(variable_configuration, variable_values):
    options = []
    for i, d in enumerate(variable_configuration.get('options', [{
            'value': _} for _ in variable_values])):
        option_value = d['value']
        options.append({
            'id': d.get('id', i),
            'name': d.get('name', option_value),
            'value': option_value})
    return options


L = getLogger(__name__)


LINK_JS_HEADER = asset_storage.load_raw_text('link-header.js')
LINK_JS_OUTPUT = asset_storage.load_string_text('link-output.js')


STRING_HTML_INPUT = asset_storage.load_jinja_text('string-input.html')
STRING_JS_INPUT = asset_storage.load_string_text('string-input.js')
STRING_JS_HEADER = asset_storage.load_raw_text('string-header.js')
STRING_JS_OUTPUT = asset_storage.load_string_text('string-output.js')


TEXT_HTML_INPUT = asset_storage.load_string_text('text-input.html')
TEXT_JS_HEADER = asset_storage.load_raw_text('text-header.js')
TEXT_JS_INPUT = asset_storage.load_string_text('text-input.js')
TEXT_JS_OUTPUT = asset_storage.load_string_text('text-output.js')


MARKDOWN_JS_HEADER = asset_storage.load_raw_text('markdown-header.js')
MARKDOWN_JS_OUTPUT = asset_storage.load_string_text('markdown-output.js')


IMAGE_JS_HEADER = asset_storage.load_raw_text('image-header.js')
IMAGE_JS_OUTPUT = asset_storage.load_string_text('image-output.js')


RADIO_HTML_INPUT = asset_storage.load_jinja_text('radio-input.html')
RADIO_JS_HEADER = asset_storage.load_raw_text('radio-header.js')
RADIO_JS_INPUT = asset_storage.load_string_text('radio-input.js')
RADIO_JS_OUTPUT = asset_storage.load_string_text('radio-output.js')


CHECKBOX_HTML_INPUT = asset_storage.load_jinja_text('checkbox-input.html')
CHECKBOX_JS_HEADER = asset_storage.load_raw_text('checkbox-header.js')
CHECKBOX_JS_INPUT = asset_storage.load_string_text('checkbox-input.js')
CHECKBOX_JS_OUTPUT = asset_storage.load_string_text('checkbox-output.js')


TABLE_JS_HEADER = asset_storage.load_raw_text('table-header.js')
TABLE_JS_OUTPUT = asset_storage.load_string_text('table-output.js')


FRAME_JS_HEADER = asset_storage.load_raw_text('frame-header.js')
FRAME_JS_OUTPUT = asset_storage.load_string_text('frame-output.js')


JSON_JS_HEADER = asset_storage.load_raw_text('json-header.js')
JSON_JS_OUTPUT = asset_storage.load_string_text('json-output.js')


YIELD_DATA_BY_ID_BY_EXTENSION = {
    '.csv': yield_data_by_id_from_csv,
    '.txt': yield_data_by_id_from_txt}


FILE_DATA_CACHE = FileCache(
    load_file_data=load_file_data,
    maximum_length=MAXIMUM_FILE_CACHE_LENGTH)

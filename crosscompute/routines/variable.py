import csv
import json
import shutil
from dataclasses import dataclass
from importlib_metadata import entry_points
from invisibleroads_macros_log import format_path
from logging import getLogger
from os.path import basename, exists
from string import Template

from ..constants import (
    FUNCTION_BY_NAME,
    MAXIMUM_FILE_CACHE_LENGTH,
    TEMPLATES_FOLDER,
    VARIABLE_ID_PATTERN)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeDataError)
from ..macros.disk import FileCache
from ..macros.package import import_attribute
from ..macros.web import (
    escape_quotes_html, escape_quotes_js)
from .interface import Batch


@dataclass(repr=False, eq=False, order=False, frozen=True)
class Element():

    id: str
    base_uri: str
    mode_name: str
    for_print: bool
    function_names: list[str]


class VariableView():

    view_name = 'variable'
    environment_variable_definitions = []

    def __init__(self, variable_definition):
        self.variable_definition = variable_definition
        self.variable_id = variable_definition.id
        self.variable_path = variable_definition.path
        self.mode_name = variable_definition.mode_name

    @classmethod
    def get_from(Class, variable_definition):
        view_name = variable_definition.view_name
        try:
            View = VARIABLE_VIEW_BY_NAME[view_name]
        except KeyError:
            L.error('%s view not installed', view_name)
            View = Class
        return View(variable_definition)

    def parse(self, data):
        return data

    def render(self, b: Batch, x: Element):
        if x.mode_name == 'input':
            render = self.render_input
        else:
            render = self.render_output
        return render(b, x)

    def render_input(self, b: Batch, x: Element):
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': '',
            'js_texts': [],
        }

    def render_output(self, b: Batch, x: Element):
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': '',
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
        name = c.get('name', basename(self.variable_path))
        text = c.get('text', name)
        body_text = (
            f'<a id="{element_id}" href="{data_uri}" '
            f'class="{self.mode_name} {self.view_name} {variable_id}" '
            f'download="{escape_quotes_html(name)}">'
            f'{text}</a>')
        js_texts = [
            LINK_HEADER,
            LINK_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'text': escape_quotes_js(text),
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }


class StringView(VariableView):

    view_name = 'string'
    input_type = 'text'
    function_by_name = FUNCTION_BY_NAME

    def get_value(self, b: Batch):
        variable_definition = self.variable_definition
        data = b.get_data(variable_definition)
        if 'value' in data:
            value = data['value']
        elif 'path' in data:
            value = FILE_TEXT_CACHE[data['path']]
        else:
            value = ''
        return value

    def render_input(self, b: Batch, x: Element):
        view_name = self.view_name
        variable_id = self.variable_id
        value = self.get_value(b)
        body_text = (
            f'<input id="{x.id}" '
            f'class="{self.mode_name} {view_name} {variable_id}" '
            f'value="{escape_quotes_html(value)}" type="{self.input_type}" '
            f'data-view="{view_name}" data-id="{variable_id}">')
        js_texts = [
            STRING_INPUT.substitute({
                'view_name': view_name,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }

    def render_output(self, b: Batch, x: Element):
        value = self.get_value(b)
        try:
            value = apply_functions(
                value, x.function_names, self.function_by_name)
        except KeyError as e:
            L.error('%s function not supported for %s', e, self.view_name)
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        body_text = (
            f'<span id="{x.id}" '
            f'class="{self.mode_name} {self.view_name} {self.variable_id}">'
            f'{value}</span>')
        js_texts = [
            STRING_HEADER,
            STRING_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }


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


class TextView(StringView):

    view_name = 'text'

    def render_input(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        view_name = self.view_name
        variable_id = self.variable_id
        body_text = (
            f'<textarea id="{x.id}" '
            f'class="{self.mode_name} {view_name} {variable_id}" '
            f'data-view="{view_name}" data-id="{variable_id}" disabled>'
            '</textarea>')
        js_texts = [
            STRING_HEADER,
            STRING_INPUT.substitute({
                'view_name': view_name,
            }),
            TEXT_HEADER,
            TEXT_INPUT.substitute({
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        body_text = (
            f'<span id="{x.id}" '
            f'class="{self.mode_name} {self.view_name} {self.variable_id}">'
            '</span>')
        js_texts = [
            STRING_HEADER,
            TEXT_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }


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
        body_text = (
            f'<span id="{x.id}" '
            f'class="{self.mode_name} {self.view_name} {self.variable_id}">'
            '</span>')
        js_texts = [
            STRING_HEADER,
            MARKDOWN_HEADER,
            MARKDOWN_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': self.js_uris,
            'body_text': body_text,
            'js_texts': js_texts,
        }


class ImageView(VariableView):

    view_name = 'image'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        body_text = (
            f'<img id="{x.id}" '
            f'class="{self.mode_name} {self.view_name} {variable_id}" '
            f'src="{data_uri}" alt="">')
        # TODO: Show spinner onerror
        js_texts = [
            IMAGE_HEADER,
            IMAGE_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }


class TableView(VariableView):

    view_name = 'table'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        element_id = x.id
        data_uri = b.get_data_uri(variable_definition, x)
        body_text = (
            f'<table id="{element_id}" '
            f'class="{self.mode_name} {self.view_name} {variable_id}">'
            '<thead/><tbody/></table>')
        js_texts = [
            TABLE_HEADER,
            TABLE_OUTPUT.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri,
            }),
        ]
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': js_texts,
        }


def save_variable_data(target_path, data_by_id, variable_definitions):
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
        variable_data = list(variable_data_by_id.values())[0]
        if 'value' in variable_data:
            open(target_path, 'wt').write(variable_data['value'])
        elif 'path' in variable_data:
            shutil.copy(variable_data['path'], target_path)
        # TODO: Download variable_data['uri']


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


def update_variable_data(target_path, data_by_id):
    try:
        if exists(target_path):
            with open(target_path, 'r+t') as f:
                d = json.load(f)
                d.update(data_by_id)
                f.seek(0)
                f.truncate()
                json.dump(d, f)
        else:
            with open(target_path, 'wt') as f:
                d = data_by_id
                json.dump(d, f)
    except (json.JSONDecodeError, OSError) as e:
        raise CrossComputeDataError(e)


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
    if path.suffix == '.dictionary':
        try:
            value = json.load(path.open('rt'))
        except (json.JSONDecodeError, OSError) as e:
            raise CrossComputeDataError(
                f'could not load {format_path(path)}: {e}')
        return {'value': value}
    if not path.exists():
        raise CrossComputeDataError(f'could not find {format_path(path)}')
    return {'path': path}


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
        text = variable_data.get('value', '')
        try:
            text = apply_functions(
                text, expression_terms[1:], FUNCTION_BY_NAME)
        except KeyError as e:
            raise CrossComputeConfigurationError(
                f'{e} function not supported in {text}')
        return str(text)

    return VARIABLE_ID_PATTERN.sub(f, text)


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


def load_view_text(file_name):
    return open(TEMPLATES_FOLDER / file_name).read().strip()


L = getLogger(__name__)


LINK_HEADER = load_view_text('linkHeader.js')
LINK_OUTPUT = Template(load_view_text('linkOutput.js'))


STRING_INPUT = Template(load_view_text('stringInput.js'))
STRING_HEADER = load_view_text('stringHeader.js')
STRING_OUTPUT = Template(load_view_text('stringOutput.js'))


TEXT_HEADER = load_view_text('textHeader.js')
TEXT_INPUT = Template(load_view_text('textInput.js'))
TEXT_OUTPUT = Template(load_view_text('textOutput.js'))


MARKDOWN_HEADER = load_view_text('markdownHeader.js')
MARKDOWN_OUTPUT = Template(load_view_text('markdownOutput.js'))


IMAGE_HEADER = load_view_text('imageHeader.js')
IMAGE_OUTPUT = Template(load_view_text('imageOutput.js'))


TABLE_HEADER = load_view_text('tableHeader.js')
TABLE_OUTPUT = Template(load_view_text('tableOutput.js'))


VARIABLE_VIEW_BY_NAME = {_.name: import_attribute(
    _.value) for _ in entry_points().select(group='crosscompute.views')}
YIELD_DATA_BY_ID_BY_EXTENSION = {
    '.csv': yield_data_by_id_from_csv,
    '.txt': yield_data_by_id_from_txt,
}


FILE_DATA_CACHE = FileCache(
    load_file_data=load_file_data,
    maximum_length=MAXIMUM_FILE_CACHE_LENGTH)
FILE_TEXT_CACHE = FileCache(
    load_file_data=load_file_text,
    maximum_length=MAXIMUM_FILE_CACHE_LENGTH)

import csv
import json
from importlib.metadata import entry_points
from invisibleroads_macros_log import format_path
from logging import getLogger
from os.path import getmtime, join, splitext

from ..constants import (
    FUNCTION_BY_NAME,
    VARIABLE_CACHE,
    VARIABLE_ID_PATTERN)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeDataError)
from ..macros.package import import_attribute
from ..macros.web import get_html_from_markdown


class VariableView():

    view_name = 'variable'
    is_asynchronous = False

    def __init__(self, variable_definition):
        self.variable_definition = variable_definition
        self.variable_id = variable_definition['id']
        self.variable_path = variable_definition['path']
        self.variable_mode = variable_definition['mode']

    @classmethod
    def get_from(Class, variable_definition):
        view_name = variable_definition['view']
        try:
            View = VIEW_BY_NAME[view_name]
        except KeyError:
            L.error('%s view not installed', view_name)
            View = Class
        return View(variable_definition)

    def load(self, absolute_batch_folder):
        self.data = self._get_data(absolute_batch_folder)
        self.configuration = self._get_configuration(absolute_batch_folder)
        return self

    def parse(self, data):
        return data

    def render(self, mode_name, element_id, function_names, request_path):
        if mode_name == 'input':
            render = self.render_input
        else:
            render = self.render_output
        return render(element_id, function_names, request_path)

    def render_input(self, element_id, function_names, request_path):
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': '',
            'js_texts': [],
        }

    def render_output(self, element_id, function_names, request_path):
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': '',
            'js_texts': [],
        }

    def _get_data(self, absolute_batch_folder):
        variable_path = self.variable_path
        if self.is_asynchronous or variable_path == 'ENVIRONMENT':
            variable_data = ''
        else:
            absolute_variable_path = join(
                absolute_batch_folder, self.variable_mode, variable_path)
            variable_data = load_variable_data(
                absolute_variable_path, self.variable_id)
        return variable_data

    def _get_configuration(self, absolute_batch_folder):
        variable_configuration = self.variable_definition.get(
            'configuration', {})
        configuration_path = variable_configuration.get('path')
        if configuration_path:
            path = join(
                absolute_batch_folder, self.variable_mode, configuration_path)
            try:
                variable_configuration.update(json.load(open(path, 'rt')))
            except OSError:
                L.error('path not found %s', format_path(path))
            except json.JSONDecodeError:
                L.error('must be json %s', format_path(path))
            except TypeError:
                L.error('must contain a dictionary %s', format_path(path))
        return variable_configuration


class StringView(VariableView):

    view_name = 'string'
    input_type = 'text'
    function_by_name = FUNCTION_BY_NAME

    def render_input(self, element_id, function_names, request_path):
        variable_id = self.variable_id
        body_text = (
            f'<input id="{element_id}" name="{variable_id}" '
            f'class="{self.view_name} {variable_id}" '
            f'value="{self.data}" type="{self.input_type}">')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }

    def render_output(self, element_id, function_names, request_path):
        try:
            data = apply_functions(
                self.data, function_names, self.function_by_name)
        except KeyError as e:
            L.error('%s function not supported for string', e)
            data = self.data
        body_text = (
            f'<span id="{element_id}" '
            f'class="{self.view_name} {self.variable_id}">'
            f'{data}</span>')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }


class NumberView(StringView):

    view_name = 'number'
    input_type = 'number'

    def parse(self, data):
        try:
            data = float(data)
        except ValueError:
            raise CrossComputeDataError(f'{data} is not a number')
        if data.is_integer():
            data = int(data)
        return data


class PasswordView(StringView):

    view_name = 'password'
    input_type = 'password'


class EmailView(StringView):

    view_name = 'email'
    input_type = 'email'


class TextView(StringView):

    view_name = 'text'

    def render_input(self, element_id, function_names, request_path):
        variable_id = self.variable_id
        body_text = (
            f'<textarea id="{element_id}" name="{variable_id}" '
            f'class="{self.view_name} {variable_id}">'
            f'{self.data}</textarea>')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }


class MarkdownView(TextView):

    view_name = 'markdown'

    def render_output(self, element_id, function_names, request_path):
        data = get_html_from_markdown(self.data)
        body_text = (
            f'<span id="{element_id}" '
            f'class="{self.view_name} {self.variable_id}">'
            f'{data}</span>')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }


class ImageView(VariableView):

    view_name = 'image'
    is_asynchronous = True

    def render_output(self, element_id, function_names, request_path):
        variable_id = self.variable_id
        body_text = (
            f'<img id="{element_id}" '
            f'class="{self.view_name} {variable_id}" '
            f'src="{request_path}/{variable_id}">')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }


def save_variable_data(target_path, variable_definitions, data_by_id):
    file_extension = splitext(target_path)[1]
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id)
    if file_extension == '.dictionary':
        with open(target_path, 'wt') as input_file:
            json.dump(variable_data_by_id, input_file)
    elif len(variable_data_by_id) > 1:
        raise CrossComputeConfigurationError(
            f'{file_extension} does not support multiple variables')
    else:
        variable_data = list(variable_data_by_id.values())[0]
        open(target_path, 'wt').write(variable_data)


def load_variable_data(path, variable_id):
    try:
        new_time = getmtime(path)
    except OSError:
        new_time = None
    key = path, variable_id
    if key in VARIABLE_CACHE:
        old_time, variable_value = VARIABLE_CACHE[key]
        if old_time == new_time:
            return variable_value
    file_extension = splitext(path)[1]
    try:
        with open(path, 'rt') as file:
            if file_extension == '.dictionary':
                value_by_id = json.load(file)
                for i, v in value_by_id.items():
                    VARIABLE_CACHE[(path, i)] = new_time, v
                value = value_by_id[variable_id]
            else:
                value = file.read().rstrip()
    except Exception:
        L.warning(f'could not load {variable_id} from {path}')
        value = ''
    VARIABLE_CACHE[(path, variable_id)] = new_time, value
    return value


def get_variable_data_by_id(variable_definitions, data_by_id):
    variable_data_by_id = {}
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        if None in data_by_id:
            variable_data = data_by_id[None]
        else:
            try:
                variable_data = data_by_id[variable_id]
            except KeyError:
                raise CrossComputeConfigurationError(
                    f'{variable_id} not defined in batch configuration')
        variable_data_by_id[variable_id] = variable_data
    return variable_data_by_id


def yield_data_by_id_from_csv(path, variable_definitions):
    try:
        with open(path, 'rt') as file:
            csv_reader = csv.reader(file)
            keys = [_.strip() for _ in next(csv_reader)]
            for values in csv_reader:
                data_by_id = parse_data_by_id(dict(zip(
                    keys, values)), variable_definitions)
                if data_by_id.get('#') == '#':
                    continue
                yield data_by_id
    except OSError:
        raise CrossComputeConfigurationError(f'{path} path not found')


def yield_data_by_id_from_txt(path, variable_definitions):
    if len(variable_definitions) > 1:
        raise CrossComputeConfigurationError(
            'use .csv to configure multiple variables')

    try:
        variable_id = variable_definitions[0]['id']
    except IndexError:
        variable_id = None

    try:
        with open(path, 'rt') as batch_configuration_file:
            for line in batch_configuration_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                yield parse_data_by_id({
                    variable_id: line}, variable_definitions)
    except OSError:
        raise CrossComputeConfigurationError(f'{path} path not found')


def parse_data_by_id(data_by_id, variable_definitions):
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        try:
            variable_data = data_by_id[variable_id]
        except KeyError:
            raise CrossComputeDataError(f'{variable_id} required')
        variable_view = VariableView.get_from(variable_definition)
        try:
            variable_data = variable_view.parse(variable_data)
        except CrossComputeDataError as e:
            raise CrossComputeDataError(f'{e} for variable {variable_id}')
        data_by_id[variable_id] = variable_data
    return data_by_id


def format_text(text, data_by_id):
    if not data_by_id:
        return text
    if None in data_by_id:
        f = data_by_id[None]
    else:
        def f(match):
            matching_text = match.group(0)
            expression_text = match.group(1)
            expression_terms = expression_text.split('|')
            variable_id = expression_terms[0].strip()
            try:
                text = data_by_id[variable_id]
            except KeyError:
                L.warning('%s missing in batch configuration', variable_id)
                return matching_text
            try:
                text = apply_functions(
                    text, expression_terms[1:], FUNCTION_BY_NAME)
            except KeyError as e:
                L.error('%s function not supported for string', e)
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


VIEW_BY_NAME = {_.name: import_attribute(_.value) for _ in entry_points()[
    'crosscompute.views']}
L = getLogger(__name__)

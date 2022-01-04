import json
from importlib.metadata import entry_points
from logging import getLogger
from os.path import getmtime, join, splitext

from ..constants import FUNCTION_BY_NAME, VARIABLE_CACHE
from ..exceptions import CrossComputeDataError
from ..macros.package import import_attribute
from ..macros.web import get_html_from_markdown
from .configuration import apply_functions


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

    def parse(self, data):
        return data

    def render(self, element_id, function_names, request_path):
        if self.variable_mode == 'input':
            render = self.render_input
        else:
            render = self.render_output
        return render(element_id, function_names, request_path)

    def _render_input(self, element_id, function_names, request_path):
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': '',
            'js_texts': [],
        }

    def _render_output(self, element_id, function_names, request_path):
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
            variable_data = load_variable_data(absolute_variable_path, self.id)
        return variable_data

    def _get_configuration(self, absolute_batch_folder):
        variable_configuration = self.variable_definition.get(
            'configuration', {})
        configuration_path = variable_configuration.get('path')
        if configuration_path:
            try:
                variable_configuration.update(json.load(open(join(
                    absolute_batch_folder, configuration_path), 'rt')))
            except OSError:
                L.error('%s not found', configuration_path)
            except json.JSONDecodeError:
                L.error('%s must be json', configuration_path)
            except TypeError:
                L.error('%s must contain a dictionary', configuration_path)
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
        # TODO: Load text asynchronously
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
        body_text = (
            f'<img id="{element_id}" '
            f'class="{self.view_name} {self.variable_id}" '
            f'src="{request_path}/{self.variable_path}">')
        return {
            'css_uris': [],
            'js_uris': [],
            'body_text': body_text,
            'js_texts': [],
        }


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


VIEW_BY_NAME = {_.name: import_attribute(_.value) for _ in entry_points()[
    'crosscompute.views']}
L = getLogger(__name__)

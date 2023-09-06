# TODO: Reduce unnecessary fetches
# TODO: Validate variable view configurations
# TODO: Rename variable_definition to variable
# TODO: Remove variable_id from class
import json
import shutil
from logging import getLogger
from os import symlink
from urllib.request import urlretrieve as download_uri

from invisibleroads_macros_log import format_path

from ..constants import (
    FILES_FOLDER,
    FILES_ROUTE,
    VARIABLE_ID_TEMPLATE_PATTERN)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationNotImplementedError,
    CrossComputeDataError)
from ..macros.iterable import find_item
from ..settings import (
    template_globals,
    view_by_name)
from .asset import (
    CHECKBOX_INPUT_HEADER_JS,
    CHECKBOX_INPUT_HTML,
    CHECKBOX_OUTPUT_HEADER_JS,
    CHECKBOX_OUTPUT_JS,
    FILE_INPUT_HEADER_JS,
    FILE_INPUT_HTML,
    FRAME_OUTPUT_HEADER_JS,
    FRAME_OUTPUT_JS,
    IMAGE_OUTPUT_HEADER_JS,
    IMAGE_OUTPUT_JS,
    JSON_OUTPUT_HEADER_JS,
    JSON_OUTPUT_JS,
    LINK_OUTPUT_HEADER_JS,
    LINK_OUTPUT_JS,
    MARKDOWN_OUTPUT_HEADER_JS,
    MARKDOWN_OUTPUT_JS,
    PDF_CSS,
    PDF_OUTPUT_HEADER_JS,
    PDF_OUTPUT_JS,
    RADIO_INPUT_HTML,
    RADIO_INPUT_HEADER_JS,
    RADIO_OUTPUT_HEADER_JS,
    RADIO_OUTPUT_JS,
    STRING_INPUT_HEADER_JS,
    STRING_INPUT_JS,
    STRING_INPUT_HTML,
    STRING_OUTPUT_HEADER_JS,
    STRING_OUTPUT_JS,
    TABLE_OUTPUT_HEADER_JS,
    TABLE_OUTPUT_JS,
    TEXT_INPUT_HTML,
    TEXT_INPUT_JS,
    TEXT_OUTPUT_HEADER_JS,
    TEXT_OUTPUT_JS)
from .interface import Batch


class VariableView:

    environment_variable_definitions = []

    def process(self, path):
        pass


class LinkView(VariableView):

    view_name = 'link'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        c = b.get_data_configuration(variable_definition)
        element_id = x.id
        variable_path = self.variable_path
        file_name = c.get(
            'file-name',
            variable_path.name if variable_path else variable_id)
        link_text = c.get('link-text', file_name)
        main_text = (
            f'<a id="{element_id}" href="{data_uri}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'download="{escape_quotes_html(file_name)}" '
            f'data-text="{escape_quotes_html(link_text)}">'
            f'{link_text}</a>')
        js_texts = [
            LINK_OUTPUT_HEADER_JS,
            LINK_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class StringView(VariableView):

    function_by_name = {
        'title': str.title}

    def render_input(self, b: Batch, x: Element):
        js_texts = [
            STRING_INPUT_HEADER_JS.substitute({'view_name': view_name})]
        if is_big_data:
            js_texts.extend([
                STRING_OUTPUT_HEADER_JS,
                STRING_INPUT_JS.substitute({
                    'element_id': element_id,
                    'data_uri': b.get_data_uri(variable_definition, x)})])

    def render_output(self, b: Batch, x: Element):
        # TODO: apply functions for data_uri
        try:
            value = apply_functions(
                value, x.function_names, self.function_by_name)
        except KeyError as e:
            L.error(
                'function "%s" not supported for view "%s"', e, self.view_name)
        data_uri = b.get_data_uri(variable_definition, x)
        js_texts = [
            STRING_OUTPUT_HEADER_JS,
            STRING_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]


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
        variable_id = self.variable_id
        view_name = self.view_name
        data_uri = b.get_data_uri(variable_definition, x)
        # TODO: load data from file, but if we get a path, do not use
        data = get_data_from(x.request_params, variable_definition)
        element_id = x.id
        value = data.get('value', '')
        main_text = TEXT_INPUT_HTML.substitute({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'attribute_string': '' if value else ' disabled',
            'value': value})
        js_texts = [
            STRING_OUTPUT_HEADER_JS,
            STRING_INPUT_HEADER_JS.substitute({'view_name': view_name})]
        if not value:
            js_texts.extend([
                TEXT_INPUT_JS.substitute({
                    'element_id': element_id,
                    'data_uri': data_uri})])
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        element_id = x.id
        main_text = (
            f'<span id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}">'
            '</span>')
        js_texts = [
            STRING_OUTPUT_HEADER_JS,
            TEXT_OUTPUT_HEADER_JS,
            TEXT_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class MarkdownView(TextView):

    view_name = 'markdown'
    js_uris = ['https://cdn.jsdelivr.net/npm/marked/marked.min.js']

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        element_id = x.id
        main_text = (
            f'<span id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}">'
            '</span>')
        js_texts = [
            STRING_OUTPUT_HEADER_JS,
            MARKDOWN_OUTPUT_HEADER_JS,
            MARKDOWN_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': self.js_uris,
            'js_texts': js_texts, 'main_text': main_text}


class ImageView(VariableView):

    view_name = 'image'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        element_id = x.id
        main_text = (
            f'<img id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'src="{data_uri}" alt="">')
        # TODO: Show spinner on error
        js_texts = [
            IMAGE_OUTPUT_HEADER_JS,
            IMAGE_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class RadioView(VariableView):

    view_name = 'radio'

    def render_input(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        view_name = self.view_name
        c = b.get_data_configuration(variable_definition)
        data = b.load_data_from(x.request_params, variable_definition)
        element_id = x.id
        value = data.get('value', '')
        main_text = RADIO_INPUT_HTML.render({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'options': get_configuration_options(
                c, [value] if value != '' else []),
            'value': value})
        js_texts = [
            RADIO_INPUT_HEADER_JS.substitute({'view_name': view_name})]
        if variable_definition.step_name != 'input':
            data_uri = b.get_data_uri(variable_definition, x)
            js_texts.extend([
                RADIO_OUTPUT_HEADER_JS,
                RADIO_OUTPUT_JS.substitute({
                    'variable_id': variable_id, 'element_id': element_id,
                    'data_uri': data_uri})])
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'main_text': main_text, 'js_texts': js_texts}


class CheckboxView(VariableView):

    view_name = 'checkbox'

    def render_input(self, b: Batch, x: Element):
        view_name = self.view_name
        variable_id = self.variable_id
        variable_definition = self.variable_definition
        c = b.get_data_configuration(variable_definition)
        data = b.load_data_from(x.request_params, variable_definition)
        element_id = x.id
        values = data.get('value', '').strip().splitlines()
        main_text = CHECKBOX_INPUT_HTML.render({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'options': get_configuration_options(c, values),
            'values': values})
        js_texts = [
            CHECKBOX_INPUT_HEADER_JS.substitute({'view_name': view_name})]
        if variable_definition.step_name != 'input':
            data_uri = b.get_data_uri(variable_definition, x)
            js_texts.extend([
                CHECKBOX_OUTPUT_HEADER_JS,
                CHECKBOX_OUTPUT_JS.substitute({
                    'variable_id': variable_id,
                    'element_id': element_id,
                    'data_uri': data_uri})])
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'main_text': main_text, 'js_texts': js_texts}


class TableView(VariableView):

    view_name = 'table'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        element_id = x.id
        main_text = (
            f'<table id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}">'
            '<thead/><tbody/></table>')
        js_texts = [
            TABLE_OUTPUT_HEADER_JS,
            TABLE_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class FrameView(VariableView):

    view_name = 'frame'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        data = b.load_data(variable_definition)
        element_id = x.id
        if 'value' in data:
            value = data['value']
        else:
            value = ''
        main_text = (
            f'<iframe id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'src="{escape_quotes_html(value)}" frameborder="0">'
            '</iframe>')
        js_texts = [
            FRAME_OUTPUT_HEADER_JS,
            FRAME_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class JsonView(VariableView):

    view_name = 'json'

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        js_texts = [
            JSON_OUTPUT_HEADER_JS,
            JSON_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'data_uri': data_uri})]
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': ''}


class PdfView(VariableView):

    view_name = 'pdf'
    css_texts = [PDF_CSS]

    def render_output(self, b: Batch, x: Element):
        variable_definition = self.variable_definition
        variable_id = self.variable_id
        data_uri = b.get_data_uri(variable_definition, x)
        element_id = x.id
        js_texts = [
            PDF_OUTPUT_HEADER_JS,
            PDF_OUTPUT_JS.substitute({
                'variable_id': variable_id,
                'element_id': element_id,
                'data_uri': data_uri})]
        main_text = (
            f'<iframe id="{element_id}" '
            f'class="_{x.mode_name} _{self.view_name} {variable_id}" '
            f'src="{data_uri}" frameborder="0">'
            '</iframe>')
        return {
            'css_uris': [], 'css_texts': self.css_texts, 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


class FileView(VariableView):

    view_name = 'file'

    def render_input(self, b: Batch, x: Element):
        view_name = self.view_name
        variable_id = self.variable_id
        variable_definition = self.variable_definition
        c = b.get_data_configuration(variable_definition)
        element_id = x.id
        mime_types = c.get('mime-types', [])
        root_uri = template_globals['root_uri']
        js_texts = [
            FILE_INPUT_HEADER_JS.substitute({
                'view_name': view_name,
                'files_uri': root_uri + FILES_ROUTE})]
        main_text = FILE_INPUT_HTML.substitute({
            'element_id': element_id,
            'mode_name': x.mode_name,
            'view_name': view_name,
            'variable_id': variable_id,
            'accept_what': ','.join(mime_types)})
        return {
            'css_uris': [], 'css_texts': [], 'js_uris': [],
            'js_texts': js_texts, 'main_text': main_text}


def link_files(path_template, variable_uri):
    folder = FILES_FOLDER / variable_uri.replace('/f/', '')
    file_dictionaries = load_file_json(folder / 'files.json')
    for file_index, file_dictionary in enumerate(file_dictionaries):
        file_path = folder / str(file_index)
        file_extension = file_dictionary['extension']
        target_path = str(path_template).format(
            index=file_index, extension=file_extension)
        symlink(file_path, target_path)
        L.debug(f'linked {file_path} to {target_path}')
        if target_path == path_template:
            break


def get_data_by_id(automation_definition, batch_definition):
    automation_folder = automation_definition.folder
    batch_folder = batch_definition.folder
    absolute_batch_folder = automation_folder / batch_folder
    input_data_by_id = get_data_by_id_from_folder(
        absolute_batch_folder / 'input',
        automation_definition.get_variable_definitions('input'))
    output_data_by_id = get_data_by_id_from_folder(
        absolute_batch_folder / 'output',
        automation_definition.get_variable_definitions('output'))
    return input_data_by_id | output_data_by_id


def update_variable_data(path, data_by_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
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


def get_variable_value_by_id(data_by_id):
    return {
        variable_id: data['value'] for variable_id, data in data_by_id.items()}


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

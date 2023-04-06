from string import Template as StringTemplate

from jinja2 import Template as JinjaTemplate

from ..constants import ASSETS_FOLDER


class AssetStorage():

    def __init__(self, folder):
        self.folder = folder

    def load_raw_text(self, file_name):
        return (self.folder / file_name).read_text().strip()

    def load_string_text(self, file_name):
        return StringTemplate(self.load_raw_text(file_name))

    def load_jinja_text(self, file_name):
        return JinjaTemplate(self.load_raw_text(file_name), trim_blocks=True)


asset_storage = AssetStorage(ASSETS_FOLDER)


LINK_JS_HEADER = asset_storage.load_raw_text('link-header.js')
LINK_JS_OUTPUT = asset_storage.load_string_text('link-output.js')


STRING_HTML_INPUT = asset_storage.load_jinja_text('string-input.html')
STRING_JS_INPUT_HEADER = asset_storage.load_string_text(
    'string-input-header.js')
STRING_JS_OUTPUT_HEADER = asset_storage.load_raw_text(
    'string-output-header.js')
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

PDF_CSS = asset_storage.load_raw_text('pdf.css')
PDF_JS_HEADER = asset_storage.load_raw_text('pdf-header.js')
PDF_JS_OUTPUT = asset_storage.load_string_text('pdf-output.js')


FILE_HTML_INPUT = asset_storage.load_string_text('file-input.html')
FILE_JS_INPUT = asset_storage.load_string_text('file-input.js')

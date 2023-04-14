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


LINK_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'link-output-header.js')
LINK_OUTPUT_JS = asset_storage.load_string_text(
    'link-output.js')


STRING_INPUT_HTML = asset_storage.load_jinja_text(
    'string-input.html')
STRING_INPUT_HEADER_JS = asset_storage.load_string_text(
    'string-input-header.js')
STRING_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'string-output-header.js')
STRING_OUTPUT_JS = asset_storage.load_string_text(
    'string-output.js')


TEXT_INPUT_HTML = asset_storage.load_string_text(
    'text-input.html')
TEXT_INPUT_JS = asset_storage.load_string_text(
    'text-input.js')
TEXT_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'text-output-header.js')
TEXT_OUTPUT_JS = asset_storage.load_string_text(
    'text-output.js')


MARKDOWN_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'markdown-output-header.js')
MARKDOWN_OUTPUT_JS = asset_storage.load_string_text(
    'markdown-output.js')


IMAGE_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'image-output-header.js')
IMAGE_OUTPUT_JS = asset_storage.load_string_text(
    'image-output.js')


RADIO_INPUT_HTML = asset_storage.load_jinja_text(
    'radio-input.html')
RADIO_INPUT_HEADER_JS = asset_storage.load_string_text(
    'radio-input-header.js')
RADIO_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'radio-output-header.js')
RADIO_OUTPUT_JS = asset_storage.load_string_text(
    'radio-output.js')


CHECKBOX_INPUT_HTML = asset_storage.load_jinja_text(
    'checkbox-input.html')
CHECKBOX_INPUT_HEADER_JS = asset_storage.load_string_text(
    'checkbox-input-header.js')
CHECKBOX_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'checkbox-output-header.js')
CHECKBOX_OUTPUT_JS = asset_storage.load_string_text(
    'checkbox-output.js')


TABLE_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'table-output-header.js')
TABLE_OUTPUT_JS = asset_storage.load_string_text(
    'table-output.js')


FRAME_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'frame-output-header.js')
FRAME_OUTPUT_JS = asset_storage.load_string_text(
    'frame-output.js')


JSON_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'json-output-header.js')
JSON_OUTPUT_JS = asset_storage.load_string_text(
    'json-output.js')


PDF_CSS = asset_storage.load_raw_text(
    'pdf.css')
PDF_OUTPUT_HEADER_JS = asset_storage.load_raw_text(
    'pdf-output-header.js')
PDF_OUTPUT_JS = asset_storage.load_string_text(
    'pdf-output.js')


FILE_INPUT_HTML = asset_storage.load_string_text(
    'file-input.html')
FILE_INPUT_HEADER_JS = asset_storage.load_string_text(
    'file-input-header.js')

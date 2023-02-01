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

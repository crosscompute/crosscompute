from importlib_metadata import entry_points

from crosscompute.macros.package import import_attribute


class BatchPrinter():

    def __init__(self, printer_configuration):
        self.server_uri = printer_configuration['uri']
        self.target_folder = printer_configuration['folder']

    def render(self, batch_dictionaries):
        pass


PRINTER_BY_NAME = {
    _.name: import_attribute(_.value)
    for _ in entry_points().select(group='crosscompute.printers')}

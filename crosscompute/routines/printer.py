from importlib_metadata import entry_points

from crosscompute.macros.package import import_attribute
from crosscompute.settings import printer_by_name


class BatchPrinter():

    def __init__(self, server_uri):
        self.server_uri = server_uri

    def render(self, batch_dictionaries, variable_configuration):
        pass


def initialize_printer_by_name():
    for entry_point in entry_points().select(group='crosscompute.printers'):
        printer_by_name[entry_point.name] = import_attribute(entry_point.value)
    return printer_by_name

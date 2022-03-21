from importlib_metadata import entry_points

from crosscompute.constants import PRINTER_BY_NAME
from crosscompute.macros.package import import_attribute


class BatchPrinter():

    def __init__(self, server_uri):
        self.server_uri = server_uri

    def render(self, batch_dictionaries, print_definition):
        pass


def initialize_printer_by_name():
    for entry_point in entry_points().select(group='crosscompute.printers'):
        PRINTER_BY_NAME[entry_point.name] = import_attribute(entry_point.value)
    return PRINTER_BY_NAME

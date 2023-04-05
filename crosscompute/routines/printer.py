from collections import defaultdict
from importlib_metadata import entry_points

from crosscompute.macros.package import import_attribute
from crosscompute.settings import printer_by_name


class BatchPrinter:

    view_name = None

    def __init__(self, server_uri, is_draft):
        self.server_uri = server_uri
        self.is_draft = is_draft
        self._packs_by_view_name = defaultdict(list)
        self._link_definitions = []

    def add(self, automation_definition, batch_definitions):
        packs_by_view_name = self._packs_by_view_name
        link_definitions = self._link_definitions
        batch_dictionaries = self._get_batch_dictionaries()
        print_configurations_by_view_name = defaultdict(list)
        print_definitions = automation_definition.get_variable_definitions(
            'print')
        for print_definition in print_definitions:
            view_name = print_definition.view_name
            if view_name in printer_by_name:
                print_configuration = print_definition.configuration
                print_configurations_by_view_name[view_name].append(
                    print_configuration)
            elif view_name == 'link':
                link_definitions.append(print_definition)
        for (
            view_name,
            print_configurations,
        ) in print_configurations_by_view_name.items():
            packs_by_view_name[view_name].append((
                batch_dictionaries, print_configurations))
        view_name = self.view_name
        if view_name and view_name not in packs_by_view_name:
            print_configurations = [{}]
            pack = batch_dictionaries, print_configurations
            packs_by_view_name = {view_name: [pack]}

    def run(self):
        packs_by_view_name = self._packs_by_view_name
        for view_name in packs_by_view_name.keys():
            packs = packs_by_view_name.pop(view_name)
            Printer = printer_by_name[view_name]
            printer = Printer(self.server_uri)
            while packs:
                batch_dictionaries, print_configurations = packs.pop()
                printer.render(batch_dictionaries, print_configurations)

    def _get_batch_dictionaries(self):
        if self.is_draft:
            print_folder
            print_name = variable_path
        else:
            print_folder = automation_folder / 'prints' / timestamp
            print_name =

        print_path = print_folder / print_path


'''
make link in batch folder
generate config in batch folder
'''


def initialize_printer_by_name():
    for entry_point in entry_points().select(group='crosscompute.printers'):
        printer_by_name[entry_point.name] = import_attribute(entry_point.value)
    return printer_by_name


def print_automation(automation_definitions, server_uri, is_draft):
    batch_printer = BatchPrinter(server_uri, is_draft)
    for automation_definition in automation_definitions:
        batch_definitions = automation_definition.batch_definitions
        batch_printer.add(automation_definition, batch_definitions)
    batch_printer.run()


def print_batch(automation_definition, batch_definition, server_uri, is_draft):
    batch_printer = BatchPrinter(server_uri, is_draft)
    batch_printer.add(automation_definition, [batch_definition])
    batch_printer.run()

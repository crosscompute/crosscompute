import json
from collections import defaultdict
from importlib_metadata import entry_points
from os import symlink

from invisibleroads_macros_disk import remove_path
from invisibleroads_macros_log import get_timestamp, LONGSTAMP_TEMPLATE

from crosscompute.macros.package import import_attribute
from crosscompute.routines.variable import (
    format_text,
    get_data_by_id)
from crosscompute.settings import printer_by_name


class BatchPrinter:

    view_name = None

    def __init__(self, server_uri, is_draft):
        self.server_uri = server_uri
        self.is_draft = is_draft
        self.reset()

    def reset(self):
        self._packs_by_view_name = defaultdict(list)
        self._pack_by_path = {}
        self._link_packs = []
        self._timestamp = get_timestamp(template=LONGSTAMP_TEMPLATE)

    def add(self, automation_definition, batch_definitions):
        packs_by_view_name = self._packs_by_view_name
        batch_dictionaries = self._get_batch_dictionaries(
            automation_definition, batch_definitions)
        print_configurations_by_view_name = defaultdict(list)
        print_definitions = automation_definition.get_variable_definitions(
            'print')
        this_view_name = self.view_name
        for print_definition in print_definitions:
            view_name = print_definition.view_name
            if this_view_name and this_view_name != view_name:
                continue
            if view_name not in printer_by_name:
                continue
            print_configuration = print_definition.configuration
            print_configurations_by_view_name[view_name].append(
                print_configuration)
        for (
            view_name,
            print_configurations,
        ) in print_configurations_by_view_name.items():
            packs_by_view_name[view_name].append((
                batch_dictionaries, print_configurations))

    def run(self):
        is_draft = self.is_draft
        if is_draft:
            for draft_path in self._pack_by_path:
                if draft_path.is_symlink():
                    remove_path(draft_path)
        for view_name, packs in self._packs_by_view_name.items():
            Printer = printer_by_name[view_name]
            printer = Printer(self.server_uri, is_draft)
            for batch_dictionaries, print_configurations in packs:
                printer.render(batch_dictionaries, print_configurations)
        self._save_link_configurations()
        self.reset()

    def _get_batch_dictionaries(
            self, automation_definition, batch_definitions):
        batch_dictionaries = []
        automation_folder = automation_definition.folder
        automation_uri = automation_definition.uri
        is_draft, pack_by_path = self.is_draft, self._pack_by_path
        link_packs, timestamp = self._link_packs, self._timestamp
        extra_data_by_id = {'timestamp': {'value': timestamp}}
        print_folder = automation_folder / 'prints' / timestamp
        for print_definition in automation_definition.get_variable_definitions(
                'print'):
            view_name = print_definition.view_name
            variable_path = print_definition.path
            for batch_definition in batch_definitions:
                batch_folder = batch_definition.folder
                batch_uri = batch_definition.uri
                draft_folder = automation_folder / batch_folder / 'print'
                if view_name in printer_by_name:
                    draft_path = draft_folder / variable_path
                    print_name = _format_print_name(
                        automation_definition, batch_definition,
                        print_definition, extra_data_by_id)
                    print_path = print_folder / print_name
                    batch_dictionaries.append({
                        'path': str(draft_path if is_draft else print_path),
                        'uri': automation_uri + batch_uri})
                    pack_by_path[draft_path] = print_folder, print_name
                elif view_name == 'link':
                    link_packs.append((draft_folder, print_definition))
        return batch_dictionaries

    def _save_link_configurations(self):
        pack_by_path = self._pack_by_path
        if not self.is_draft:
            for draft_path, (
                print_folder, print_name,
            ) in pack_by_path.items():
                symlink(print_folder / print_name, remove_path(draft_path))
        for (
            draft_folder, variable_definition,
        ) in self._link_packs:
            variable_configuration = variable_definition.configuration
            if 'path' not in variable_configuration:
                continue
            variable_path = variable_definition.path
            draft_path = draft_folder / variable_path
            print_name = pack_by_path[draft_path][1]
            d = {}
            if 'link-text' not in variable_configuration:
                d['link-text'] = print_name
            if 'file-name' not in variable_configuration:
                d['file-name'] = print_name
            with (
                draft_folder / variable_configuration['path']
            ).open('wt') as f:
                json.dump(d, f)


def initialize_printer_by_name():
    for entry_point in entry_points().select(group='crosscompute.printers'):
        printer_by_name[entry_point.name] = import_attribute(entry_point.value)
    return printer_by_name


def print_batch(automation_definition, batch_definition, server_uri, is_draft):
    batch_printer = BatchPrinter(server_uri, is_draft)
    batch_printer.add(automation_definition, [batch_definition])
    batch_printer.run()


def _format_print_name(
        automation_definition, batch_definition, print_definition,
        extra_data_by_id):
    view_name = print_definition.view_name
    variable_configuration = print_definition.configuration
    batch_name = batch_definition.name
    name_template = variable_configuration.get(
        'name', '').strip() or f'{batch_name}.{view_name}'
    data_by_id = get_data_by_id(
        automation_definition, batch_definition) | extra_data_by_id
    return format_text(name_template, data_by_id)

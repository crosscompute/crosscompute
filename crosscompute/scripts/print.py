from argparse import ArgumentParser
from logging import getLogger

from invisibleroads_macros_disk import make_folder
from invisibleroads_macros_log import get_timestamp, LONGSTAMP_TEMPLATE
from invisibleroads_macros_web.port import find_open_port

from crosscompute.constants import (
    MAXIMUM_PORT,
    MINIMUM_PORT)
from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.routines.automation import (
    DiskAutomation, run_automation)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.routines.work import (
    format_batch_name)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    configure_running_from)
from crosscompute.scripts.serve import (
    configure_argument_parser_for_serving,
    configure_serving_from,
    serve_with)
from crosscompute.settings import (
    StoppableProcess,
    printer_by_name)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        configure_serving_from(args)
        configure_running_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
        print_with(automation, args)
    except CrossComputeError as e:
        L.error(e)
        return


def print_with(automation, args):
    args.port = _get_port_or_raise_exception()
    _run(automation, args)
    _print(automation, args)
    _link(automation, args)


def _get_port_or_raise_exception():
    try:
        port = find_open_port(
            minimum_port=MINIMUM_PORT, maximum_port=MAXIMUM_PORT)
    except OSError as e:
        raise CrossComputeError(e)
    return port


def _run(automation, args):
    user_environment = args.environment
    for automation_definition in automation.definitions:
        if automation_definition.get_variable_definitions('print'):
            run_automation(
                automation_definition, user_environment, with_rebuild=True)


def _print(automation, args):
    group packs by view name
        path is in pritn folder vs path is in batch folder
    for each view name, packs
        start printer
        render packs with batch dictionaries and print configurations
    make links
        if path in print folder, then
            make link in batch folder
        generate config in batch folder

    # get batch dictionaries

        for automation_definition in automation_definitions:
            print_definitions = automation_definition.get_variable_definitions(
                'print')
        print_batches(automation_definition, batch_definitions, server_uri)


    args.with_browser, args.with_restart = False, False
    server_process = StoppableProcess(name='serve', target=serve_with, args=(
        automation, args))
    server_process.start()
    server_uri = f'http://127.0.0.1:{args.port}{args.root_uri}'
    try:
        for print_definition, batch_dictionaries in packs:
            view_name = print_definition.view_name
            print_configuration = print_definition.configuration
            Printer = printer_by_name[view_name]
            printer = Printer(server_uri)
            printer.render(batch_dictionaries, print_configuration)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        server_process.stop()
    _render_links()


def _get_batch_dictionaries(
        automation_definition, print_definition, timestamp):
    batch_dictionaries = []
    automation_folder = automation_definition.folder
    automation_uri = automation_definition.uri
    variable_id = print_definition.id
    folder = automation_folder / 'prints' / timestamp
    extra_data_by_id = {'timestamp': {'value': timestamp}}
    for batch_definition in automation_definition.batch_definitions:
        batch_uri = batch_definition.uri
        path = folder / format_batch_name(
            automation_definition, batch_definition, print_definition,
            extra_data_by_id)
        batch_dictionaries.append({
            'path': str(path),
            'uri': automation_uri + batch_uri})
    return batch_dictionaries


def _render_prints(args, packs, automation, server_uri):
        for print_definition, batch_dictionaries in packs:
            view_name = print_definition.view_name
            if view_name not in printer_by_name:
                continue
            print_configuration = print_definition.configuration
            Printer = printer_by_name[view_name]
            printer = Printer(server_uri)
            printer.render(batch_dictionaries, print_configuration)
        for print_definition, batch_dictionaries in packs:
            for batch_dictionary in batch_dictionaries:
                pass


def _render_links():
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        print_definitions = automation_definition.get_variable_definitions(
            'print')
        for batch_definition in batch_definitions:
            batch_folder = batch_definition.folder
            print_folder = make_folder(automation_folder / batch_folder / 'print')
            name_by_path = {}
            link_definitions = []
            for print_definition in print_definitions:
                print_path = print_folder / print_definition.path
                remove_path(print_path)
                symlink(batch_dictionary['path'], print_path)
                if view_name == 'link':
                    pass
            _save_link_configurations(print_folder, name_by_path, link_definitions)

L = getLogger(__name__)


if __name__ == '__main__':
    do()

from argparse import ArgumentParser
from logging import getLogger

from invisibleroads_macros_disk import make_folder, make_random_folder
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


def configure_printing_from(args):
    print_folder = args.print_folder
    if print_folder:
        make_folder(print_folder)
    else:
        args.print_folder = make_random_folder()


def print_with(automation, args):
    try:
        port = find_open_port(
            minimum_port=MINIMUM_PORT, maximum_port=MAXIMUM_PORT)
    except OSError as e:
        raise CrossComputeError(e)
    packs = []
    timestamp = get_timestamp(template=LONGSTAMP_TEMPLATE)
    for automation_definition in automation.definitions:
        print_definitions = automation_definition.get_variable_definitions(
            'print')
        if not print_definitions:
            continue
        run_automation(
            automation_definition, args.environment, with_rebuild=True)
        for print_definition in print_definitions:
            packs.append((print_definition, _get_batch_dictionaries(
                automation_definition, print_definition, timestamp)))
    args.port, args.with_browser, args.with_restart = port, False, False
    server_process = StoppableProcess(
        name='serve', target=serve_with, args=(automation, args))
    server_process.start()
    try:
        _render_prints(f'http://127.0.0.1:{port}{args.root_uri}', packs)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        server_process.stop()


def _get_batch_dictionaries(
        automation_definition, print_definition, timestamp):
    batch_dictionaries = []
    automation_folder = automation_definition.folder
    automation_uri = automation_definition.uri
    variable_id = print_definition.id
    folder = automation_folder / 'prints' / f'{variable_id}-{timestamp}'
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


def _render_prints(server_uri, packs):
    for print_definition, batch_dictionaries in packs:
        view_name = print_definition.view_name
        if view_name not in printer_by_name:
            continue
        print_configuration = print_definition.configuration
        Printer = printer_by_name[view_name]
        printer = Printer(server_uri)
        printer.render(batch_dictionaries, print_configuration)
        # TODO: add symbolic link in batch folder
        # TODO: generate download configs


L = getLogger(__name__)


if __name__ == '__main__':
    do()

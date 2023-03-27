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
from crosscompute.routines.variable import (
    format_text,
    get_data_by_id)
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
    timestamp = get_timestamp(template=LONGSTAMP_TEMPLATE)
    packs = []
    for automation_definition in automation.definitions:
        ds = automation_definition.get_variable_definitions('print')
        if not ds:
            continue
        run_automation(
            automation_definition, args.environment, with_rebuild=True)
        for variable_definition in ds:
            variable_configuration = variable_definition.configuration
            packs.append((variable_configuration, get_batch_dictionaries(
                automation_definition, variable_definition, timestamp)))
    args.port, args.with_browser, args.with_restart = port, False, False
    server_process = StoppableProcess(
        name='serve', target=serve_with, args=(automation, args))
    server_process.start()
    try:
        for variable_configuration, batch_dictionaries in packs:
            Printer = printer_by_name[variable_definition.view_name]
            printer = Printer(f'http://127.0.0.1:{port}{args.root_uri}')
            printer.render(batch_dictionaries, variable_configuration)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        server_process.stop()


def get_batch_dictionaries(
        automation_definition, variable_definition, timestamp):
    batch_dictionaries = []
    automation_folder = automation_definition.folder
    automation_uri = automation_definition.uri
    variable_id = variable_definition.id
    view_name = variable_definition.view_name
    variable_configuration = variable_definition.configuration
    name = variable_configuration.get('name', '').strip()
    folder = automation_folder / 'prints' / f'{variable_id}-{timestamp}'
    extra_data_by_id = {'timestamp': {'value': timestamp}}
    for batch_definition in automation_definition.batch_definitions:
        batch_name = batch_definition.name
        batch_uri = batch_definition.uri
        name_template = name or f'{batch_name}.{view_name}'
        data_by_id = get_data_by_id(
            automation_definition, batch_definition) | extra_data_by_id
        path = format_text(folder / name_template, data_by_id)
        batch_dictionaries.append({
            'path': path, 'uri': automation_uri + batch_uri})
    return batch_dictionaries


L = getLogger(__name__)


if __name__ == '__main__':
    do()

from argparse import ArgumentParser
from invisibleroads_macros_disk import make_folder, make_random_folder
from logging import getLogger

from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.macros.process import LoggableProcess, StoppableProcess
from crosscompute.macros.web import is_port_in_use
from crosscompute.routines.automation import DiskAutomation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.routines.printer import (
    PRINTER_BY_NAME)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    run_with)
from crosscompute.scripts.serve import (
    configure_argument_parser_for_serving,
    configure_serving_from,
    serve_with)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    configure_argument_parser_for_printing(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        configure_serving_from(args)
        configure_printing_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    print_with(automation, args)


def configure_argument_parser_for_printing(a):
    a.add_argument(
        '--print', metavar='X', dest='print_format',
        help='print automations in specific format')
    a.add_argument(
        '--print-folder', metavar='X',
        help='print automations to this folder')


def configure_printing_from(args):
    print_format = args.print_format
    if not print_format:
        return
    try:
        PRINTER_BY_NAME[print_format]
    except KeyError:
        printer_names = PRINTER_BY_NAME.keys()
        if printer_names:
            extra_message = 'try ' + ' '.join(printer_names)
        else:
            extra_message = 'install crosscompute-printers-pdf'
        raise CrossComputeError(
            f'{print_format} is not a supported printer; {extra_message}')
    args.with_browser = False
    args.is_static = True
    args.is_production = True
    print_folder = args.print_folder
    if print_folder:
        make_folder(print_folder)
    else:
        args.print_folder = make_random_folder()


def print_with(automation, args):
    if is_port_in_use(args.port, with_log=True):
        raise SystemExit
    server_process = StoppableProcess(
        name='serve', target=serve_with, args=(automation, args))
    server_process.start()
    runner_process = LoggableProcess(
        name='run', target=run_with, args=(automation, args))
    runner_process.start()
    runner_process.join()
    print_format = args.print_format
    print_folder = args.print_folder
    Printer = PRINTER_BY_NAME[print_format]
    batch_dictionaries = []
    for automation_definition in automation.definitions:
        automation_uri = automation_definition.uri
        for batch_definition in automation_definition.batch_definitions:
            name = batch_definition.name
            uri = automation_uri + batch_definition.uri
            batch_dictionaries.append({'name': name, 'uri': uri})
    configuration = automation.configuration
    print_definition = configuration.print_definition
    printer = Printer({
        'uri': f'http://127.0.0.1:{args.port}{args.base_uri}',
        'folder': print_folder})
    printer.render(batch_dictionaries, print_definition)
    server_process.stop()


L = getLogger(__name__)


if __name__ == '__main__':
    do()

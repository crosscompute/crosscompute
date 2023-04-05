from argparse import ArgumentParser
from logging import getLogger

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
from crosscompute.routines.printer import (
    BatchPrinter)
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
    StoppableProcess)


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
    args.with_browser, args.with_restart = False, False
    server_process = StoppableProcess(name='serve', target=serve_with, args=(
        automation, args))
    server_process.start()
    server_uri = f'http://127.0.0.1:{args.port}{args.root_uri}'
    try:
        batch_printer = BatchPrinter(server_uri, is_draft=False)
        for automation_definition in automation.definitions:
            batch_definitions = automation_definition.batch_definitions
            batch_printer.add(automation_definition, batch_definitions)
        batch_printer.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        server_process.stop()


L = getLogger(__name__)


if __name__ == '__main__':
    do()

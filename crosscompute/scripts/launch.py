import multiprocessing as mp
from argparse import ArgumentParser
from logging import getLogger

from crosscompute.exceptions import (
    CrossComputeConfigurationNotFoundError,
    CrossComputeError)
from crosscompute.macros.process import LoggableProcess
from crosscompute.macros.web import is_port_in_use
from crosscompute.routines.automation import DiskAutomation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring,
    configure_with)
from crosscompute.scripts.print import (
    configure_argument_parser_for_printing,
    configure_printing_from,
    print_with)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    run_with)
from crosscompute.scripts.serve import (
    configure_argument_parser_for_serving,
    configure_serving_from,
    serve_with)


def do(arguments=None):
    mp.set_start_method('fork')
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_launching(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    configure_argument_parser_for_printing(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        configure_serving_from(args)
        configure_printing_from(args)
    except CrossComputeError as e:
        L.error(e)
        return
    launch_mode = get_launch_mode_from(args)

    if launch_mode == 'configure':
        configure_with(args)
        raise SystemExit
    automation = get_automation_from(args)
    if launch_mode == 'print':
        print_with(automation, args)
        raise SystemExit
    processes = []
    if launch_mode in ['serve', 'all']:
        if is_port_in_use(args.port, with_log=True):
            raise SystemExit
        processes.append(LoggableProcess(
            name='serve', target=serve_with, args=(automation, args)))
    if launch_mode in ['run', 'all']:
        processes.append(LoggableProcess(
            name='run', target=run_with, args=(automation, args)))
    try:
        for process in processes:
            process.start()
        for process in reversed(processes):
            process.join()
    except KeyboardInterrupt:
        L.info('waiting for processes to stop')


def configure_argument_parser_for_launching(a):
    a.add_argument(
        '--configure', dest='is_configure_only', action='store_true',
        help='configure only')
    a.add_argument(
        '--serve', dest='is_serve_only', action='store_true',
        help='serve only')
    a.add_argument(
        '--run', dest='is_run_only', action='store_true',
        help='run only')
    '''
    a.add_argument(
        '--debug', dest='is_debug_only', action='store_true',
        help='debug only')
    '''


def get_launch_mode_from(args):
    launch_mode = 'all'
    if args.is_configure_only:
        launch_mode = 'configure'
    elif args.is_run_only:
        launch_mode = 'run'
    elif args.is_serve_only:
        launch_mode = 'serve'
    elif args.print_format:
        launch_mode = 'print'
    '''
    elif args.is_debug_only:
        launch_mode = 'debug'
    '''
    return launch_mode


def get_automation_from(args):
    path_or_folder = args.path_or_folder
    try:
        automation = DiskAutomation.load(path_or_folder or '.')
    except CrossComputeConfigurationNotFoundError:
        L.info('existing configuration not found; configuring new automation')
        print()
        path = configure_with(args)
        automation = DiskAutomation.load(path)
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    return automation


L = getLogger(__name__)


if __name__ == '__main__':
    do()

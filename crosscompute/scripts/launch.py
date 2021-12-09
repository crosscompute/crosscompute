from argparse import ArgumentParser
from logging import getLogger
from multiprocessing import Process

from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring,
    configure_with)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running, run_with)
from crosscompute.scripts.serve import (
    check_port, configure_argument_parser_for_serving, serve_with)


L = getLogger(__name__)


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
    a.add_argument(
        '--debug', dest='is_debug_only', action='store_true',
        help='debug only')


def get_launch_mode_from(args):
    launch_mode = 'all'
    if args.is_configure_only:
        launch_mode = 'configure'
    elif args.is_run_only:
        launch_mode = 'run'
    elif args.is_serve_only:
        launch_mode = 'serve'
    elif args.is_debug_only:
        launch_mode = 'debug'
    L.debug(f'launch_mode = {launch_mode}')
    return launch_mode


def do():
    a = ArgumentParser()
    configure_argument_parser_for_launching(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_running(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args()
    configure_logging_from(args)
    launch_mode = get_launch_mode_from(args)

    if launch_mode == 'configure':
        configure_with(args)
        raise SystemExit
    path_or_folder = args.path_or_folder
    try:
        automation = Automation.load(path_or_folder or '.')
    except CrossComputeConfigurationError as e:
        L.error(e)
        raise SystemExit
    except CrossComputeError:
        L.info('existing configuration not found; configuring new automation')
        print()
        path = configure_with(args)
        automation = Automation.load(path)

    processes = []
    if launch_mode in ['serve', 'all']:
        check_port(args.port)
        server_process = Process(target=serve_with, args=(automation, args))
        server_process.start()
        processes.append(server_process)
    if launch_mode in ['run', 'all']:
        worker_process = Process(target=run_with, args=(automation, args))
        worker_process.start()
        processes.append(worker_process)
    try:
        for process in reversed(processes):
            process.join()
    except KeyboardInterrupt:
        print()
        L.info('please wait for processes to terminate')


if __name__ == '__main__':
    do()

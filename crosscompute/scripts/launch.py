import logging
from argparse import ArgumentParser
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
    configure_argument_parser_for_serving, serve_with)


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
    elif args.is_serve_only:
        launch_mode = 'serve'
    elif args.is_run_only:
        launch_mode = 'run'
    elif args.is_debug_only:
        launch_mode = 'debug'
    return launch_mode


def do():
    a = ArgumentParser()
    configure_argument_parser_for_launching(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args()
    configure_logging_from(args)
    launch_mode = get_launch_mode_from(args)

    if launch_mode == 'configure':
        configure_with(args)
        exit()

    path_or_folder = args.path_or_folder
    try:
        automation = Automation.load(path_or_folder or '.')
    except CrossComputeConfigurationError as e:
        logging.error(e)
        exit()
    except CrossComputeError:
        logging.info(
            'existing configuration not found; configuring new automation')
        print()
        path = configure_with(args)
        automation = Automation.load(path)

    processes = []
    if launch_mode in ['serve', 'all']:
        server_process = Process(target=serve_with, args=(automation, args))
        server_process.start()
        processes.append(server_process)
    if launch_mode in ['run', 'all']:
        worker_process = Process(target=run_with, args=(automation, args))
        worker_process.start()
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    do()

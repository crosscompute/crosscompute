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


def do():
    a = ArgumentParser()
    a.add_argument(
        '--serve', dest='is_serve_only', action='store_true',
        help='serve only')
    a.add_argument(
        '--run', dest='is_run_only', action='store_true',
        help='run only')
    a.add_argument(
        '--debug', dest='is_debug_only', action='store_true',
        help='debug only')
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args()
    configure_logging_from(args)

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
    if not args.is_run_only and not args.is_debug_only:
        server_process = Process(target=serve_with, args=(automation, args))
        server_process.start()
        processes.append(server_process)
    if not args.is_debug_only and not args.is_serve_only:
        worker_process = Process(target=run_with, args=(automation, args))
        worker_process.start()
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    do()

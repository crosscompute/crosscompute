from logging import getLogger
from multiprocessing import Process

from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from crosscompute.routines.automation import Automation
from crosscompute.scripts.run import (
    configure_argument_parser_for_running, run_with)
from crosscompute.scripts.serve import (
    check_port, configure_argument_parser_for_serving, serve_with)


L = getLogger(__name__)


def do():
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
        processes.append(Process(target=serve_with, args=(automation, args)))
    if launch_mode in ['run', 'all']:
        processes.append(Process(target=run_with, args=(automation, args)))
    try:
        for process in processes:
            process.start()
        for process in reversed(processes):
            process.join()
    except KeyboardInterrupt:
        print()
        L.info('waiting for processes to stop')

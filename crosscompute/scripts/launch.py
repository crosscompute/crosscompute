from argparse import ArgumentParser
from logging import getLogger

from crosscompute import __version__
from crosscompute.constants import (
    LOGGING_LEVEL_BY_PACKAGE_NAME)
from crosscompute.exceptions import (
    CrossComputeConfigurationNotFoundError,
    CrossComputeError)
from crosscompute.macros.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.routines.automation import (
    DiskAutomation)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring,
    configure_with)
from crosscompute.scripts.print import (
    print_with)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    configure_running_from,
    run_with)
from crosscompute.scripts.serve import (
    check_port,
    configure_argument_parser_for_serving,
    configure_serving_from,
    serve_with)
from crosscompute.settings import (
    StoppableProcess)


def do(arguments=None):
    args = _get_args(arguments)
    L.info(f'launching crosscompute {__version__}')
    launch_id = get_launch_id_from(args)
    if launch_id == 'configure':
        configure_with(args)
        return
    automation = _get_automation_from(args)
    if launch_id == 'print':
        print_with(automation, args)
        return
    if launch_id in ['serve', 'all']:
        check_port(args.port)
        process = StoppableProcess(
            name='serve', target=serve_with, args=(automation, args))
    elif launch_id in ['run']:
        process = StoppableProcess(
            name='run', target=run_with, args=(automation, args))
    try:
        process.start()
        process.join()
    except KeyboardInterrupt:
        L.info('waiting for process to stop')
    except Exception as e:
        L.exception(e)
    finally:
        process.stop()


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
        '--print', dest='is_print_only', action='store_true',
        help='print only')
    a.add_argument(
        '--version', dest='is_version_only', action='store_true',
        help='show version')


def get_launch_id_from(args):
    launch_id = 'all'
    if args.is_configure_only:
        launch_id = 'configure'
    elif args.is_run_only:
        launch_id = 'run'
    elif args.is_serve_only:
        launch_id = 'serve'
    elif args.is_print_only:
        launch_id = 'print'
    return launch_id


def _get_args(arguments):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_launching(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    if args.is_version_only:
        print(__version__)
        raise SystemExit
    try:
        configure_logging_from(args, LOGGING_LEVEL_BY_PACKAGE_NAME)
        configure_serving_from(args)
        configure_running_from(args)
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    return args


def _get_automation_from(args):
    path_or_folder = args.path_or_folder
    try:
        automation = DiskAutomation.load(path_or_folder or '.')
    except CrossComputeConfigurationNotFoundError:
        L.info(
            'existing configuration was not found; configuring new automation')
        print()
        configure_with(args)
        raise SystemExit
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    return automation


L = getLogger(__name__)


if __name__ == '__main__':
    do()

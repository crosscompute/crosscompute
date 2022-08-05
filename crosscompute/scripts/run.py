from argparse import ArgumentParser
from logging import getLogger

from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.routines.automation import (
    DiskAutomation)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    run_with(automation, args)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--no-rebuild', dest='with_rebuild', action='store_false',
        help='do not rebuild batches and container images')


def run_with(automation, args):
    return run(automation, args.with_rebuild)


def run(
        automation,
        with_rebuild=True):
    try:
        automation.run(with_rebuild)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


L = getLogger(__name__)


if __name__ == '__main__':
    do()

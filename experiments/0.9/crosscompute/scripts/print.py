from argparse import ArgumentParser
from logging import getLogger

from crosscompute.constants import (
    LOGGING_LEVEL_BY_PACKAGE_NAME)
from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.macros.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.routines.automation import (
    DiskAutomation)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    configure_running_from)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args, LOGGING_LEVEL_BY_PACKAGE_NAME)
        configure_running_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
        print_with(automation, args)
    except CrossComputeError as e:
        L.error(e)
        return


def print_with(automation, args):
    automation.print(args.environment)


L = getLogger(__name__)


if __name__ == '__main__':
    do()

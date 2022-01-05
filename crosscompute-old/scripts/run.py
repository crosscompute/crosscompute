# TODO: Validate configuration
# TODO: Implement clean


from argparse import ArgumentParser
from logging import getLogger

from crosscompute.exceptions import CrossComputeError
from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)

from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


L = getLogger(__name__)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--clean', dest='with_clean', action='store_true',
        help='delete batch folders before running')


def run_with(automation, args):
    try:
        automation.run()
    except CrossComputeError as e:
        L.error(e)


def do():
    a = ArgumentParser()
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args()
    configure_logging_from(args)

    automation = Automation.load(args.path_or_folder)
    run_with(automation, args)

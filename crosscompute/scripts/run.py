# TODO: Validate configuration
# TODO: Support case when user does not specify configuration file
# TODO: Improve output when running batches
# TODO: Support multiple configuration paths
# TODO: Implement clean


from argparse import ArgumentParser

from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--clean', dest='with_clean', action='store_true',
        help='delete batch folders before running')


def run_with(automation, args):
    automation.run()


def do():
    a = ArgumentParser()
    a.add_argument('configuration_path')
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args()
    configure_logging_from(args)

    automation = Automation.load(args.configuration_path)
    run_with(automation, args)


if __name__ == '__main__':
    do()

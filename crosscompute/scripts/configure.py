from argparse import ArgumentParser

from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_VERSION,
    CONFIGURATION)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def configure_with(args):
    configuration = CONFIGURATION.copy()

    automation_name = input(
        'automation_name [%s]: ' % AUTOMATION_NAME)
    automation_version = input(
        'automation_version [%s]: ' % AUTOMATION_VERSION)

    configuration['name'] = automation_name or AUTOMATION_NAME
    configuration['version'] = automation_version or AUTOMATION_VERSION
    print(configuration)


def do():
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    args = a.parse_args()
    configure_logging_from(args)

    configure_with(args)


if __name__ == '__main__':
    do()

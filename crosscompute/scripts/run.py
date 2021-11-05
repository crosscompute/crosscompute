# TODO: Validate configuration
# TODO: Support case when user does not specify configuration file
# TODO: Improve output when running batches


from argparse import ArgumentParser

from crosscompute import Automation
from crosscompute.routines import (
    configure_argument_parser_for_logging,
    configure_logging_from)


if __name__ == '__main__':
    a = ArgumentParser()
    a.add_argument('configuration_path')
    configure_argument_parser_for_logging(a)
    args = a.parse_args()

    configure_logging_from(args)

    automation = Automation.load(args.configuration_path)
    automation.run()

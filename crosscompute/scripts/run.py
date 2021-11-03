# TODO: Separate configuration validation
# TODO: Support case when user does not specify configuration file
# TODO: Improve output when running batches


from argparse import ArgumentParser

from crosscompute import Automation
from crosscompute.routines import (
    configure_argument_parser_for_logging,
    configure_logging)


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        'configuration_path')
    configure_argument_parser_for_logging(argument_parser)
    args = argument_parser.parse_args()

    configure_logging(args.verbosity)

    automation = Automation.load(args.configuration_path)
    automation.run()

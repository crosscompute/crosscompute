from argparse import ArgumentParser

from crosscompute import Automation
from crosscompute.constants import HOST, PORT
from crosscompute.routines import (
    configure_argument_parser_for_logging,
    configure_logging_from)


if __name__ == '__main__':
    a = ArgumentParser()
    a.add_argument(
        '--host',
        default=HOST)
    a.add_argument(
        '--port',
        default=PORT)
    a.add_argument(
        '--static',
        dest='is_static',
        action='store_true')
    a.add_argument('configuration_path')
    configure_argument_parser_for_logging(a)
    args = a.parse_args()

    configure_logging_from(args)

    automation = Automation.load(
        args.configuration_path)
    automation.serve(
        args.host,
        args.port,
        args.is_static)

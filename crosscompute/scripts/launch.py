from argparse import ArgumentParser

from crosscompute.routines.log import (
    configure_argument_parser_for_logging)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--clean', dest='with_clean', action='store_true',
        help='delete batch folders before running')


def configure_argument_parser_for_serving(a):
    pass


def do():
    a = ArgumentParser()
    a.add_argument(
        'configuration_path',
        help='automation configuration path',
        nargs='?')
    a.add_argument(
        '--run', dest='with_run', action='store_true',
        help='run in foreground')
    a.add_argument(
        '--debug', dest='with_debug', action='store_true',
        help='debug in foreground')
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_running(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args()
    print(args)


'''
crosscompute
    # Walk through new configuration
    # Serve
    # Run in background
'''


if __name__ == '__main__':
    do()

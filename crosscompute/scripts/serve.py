from argparse import ArgumentParser

from crosscompute.constants import (
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT)
from crosscompute.macros import open_browser
from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def configure_argument_parser_for_serving(a):
    a.add_argument(
        '--host', metavar='X',
        default=HOST,
        help='specify 0.0.0.0 to listen for requests on all ip addresses')
    a.add_argument(
        '--port', metavar='X',
        default=PORT,
        help='specify port to listen to for requests')
    a.add_argument(
        '--production', dest='is_production', action='store_true',
        help='disable server restart on file change')
    a.add_argument(
        '--static', dest='is_static', action='store_true',
        help='disable page update on file change')
    a.add_argument(
        '--disk-poll', metavar='X', type=int,
        default=DISK_POLL_IN_MILLISECONDS,
        help='interval in milliseconds to check disk for changes')
    a.add_argument(
        '--disk-debounce', metavar='X', type=int,
        default=DISK_DEBOUNCE_IN_MILLISECONDS,
        help='interval in milliseconds to wait until the disk stops changing')


def serve_with(automation, args):
    open_browser(f'http://localhost:{args.port}')
    automation.serve(
        host=args.host,
        port=args.port,
        is_production=args.is_production,
        is_static=args.is_static,
        disk_poll_in_milliseconds=args.disk_poll,
        disk_debounce_in_milliseconds=args.disk_debounce)


def do():
    a = ArgumentParser()
    a.add_argument('configuration_path')
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args()
    configure_logging_from(args)

    automation = Automation.load(args.configuration_path)
    serve_with(automation, args)


if __name__ == '__main__':
    do()

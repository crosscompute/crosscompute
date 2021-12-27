from argparse import ArgumentParser
from logging import getLogger
from os import environ

from crosscompute.constants import (
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT)
from crosscompute.macros import (is_port_in_use, open_browser)
from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)

from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


L = getLogger(__name__)


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
        '--no-browser',
        dest='with_browser',
        action='store_false',
        help='do not open browser')
    a.add_argument(
        '--base-uri', metavar='X',
        default='',
        help='specify base uri for all routes')
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


def check_port(port):
    if is_port_in_use(port):
        L.error('port=%s is in use; cannot start server', port)
        raise SystemExit
    return port


def serve_with(automation, args):
    if args.with_browser and 'DISPLAY' in environ:
        L.info('opening browser; set --no-browser to disable')
        open_browser(f'http://localhost:{args.port}{args.base_uri}')
    try:
        automation.serve(
            host=args.host,
            port=args.port,
            base_uri=args.base_uri,
            is_production=args.is_production,
            is_static=args.is_static,
            disk_poll_in_milliseconds=args.disk_poll,
            disk_debounce_in_milliseconds=args.disk_debounce)
    except KeyboardInterrupt:
        pass


def do():
    a = ArgumentParser()
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args()
    configure_logging_from(args)

    check_port(args.port)
    automation = Automation.load(args.path_or_folder)
    serve_with(automation, args)


if __name__ == '__main__':
    do()

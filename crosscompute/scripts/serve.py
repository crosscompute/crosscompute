from argparse import ArgumentParser
from logging import getLogger
from os import environ

from crosscompute.constants import (
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT)
from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.macros.web import is_port_in_use, open_browser
from crosscompute.routines.automation import Automation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


def do():
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args()
    configure_logging_from(args)
    try:
        automation = Automation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    serve_with(automation, args)


def configure_argument_parser_for_serving(a):
    a.add_argument(
        '--host', metavar='X',
        default=HOST,
        help='specify 0.0.0.0 to listen for requests from all ip addresses')
    a.add_argument(
        '--port', metavar='X',
        default=PORT,
        help='specify port to listen to for requests')
    a.add_argument(
        '--no-browser', dest='with_browser', action='store_false',
        help='do not open browser')
    a.add_argument(
        '--static', dest='is_static', action='store_true',
        help='disable page update on file change')
    a.add_argument(
        '--production', dest='is_production', action='store_true',
        help='disable server restart on file change')
    a.add_argument(
        '--disk-poll', metavar='X', type=int,
        default=DISK_POLL_IN_MILLISECONDS,
        help='interval in milliseconds to check disk for changes')
    a.add_argument(
        '--disk-debounce', metavar='X', type=int,
        default=DISK_DEBOUNCE_IN_MILLISECONDS,
        help='interval in milliseconds to wait until the disk stops changing')
    a.add_argument(
        '--base-uri', metavar='X',
        default='',
        help='specify base uri for all routes')


def serve_with(automation, args):
    host, port, base_uri = args.host, args.port, args.base_uri
    try:
        if is_port_in_use(port):
            raise CrossComputeError(
                'port=%s is in use; cannot start server', port)
        if args.with_browser and 'DISPLAY' in environ:
            L.info('opening browser; set --no-browser to disable')
            open_browser(f'http://localhost:{port}{base_uri}')
        automation.serve(
            host=host,
            port=port,
            is_static=args.is_static,
            is_production=args.is_production,
            disk_poll_in_milliseconds=args.disk_poll,
            disk_debounce_in_milliseconds=args.disk_debounce,
            base_uri=base_uri)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


L = getLogger(__name__)


if __name__ == '__main__':
    do()

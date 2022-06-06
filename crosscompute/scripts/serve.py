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
from crosscompute.macros.web import (
    find_open_port, is_port_in_use, open_browser)
from crosscompute.routines.automation import DiskAutomation
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        configure_serving_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    check_port(args.port)
    serve_with(automation, args)


def configure_argument_parser_for_serving(a):
    a.add_argument(
        '--host', metavar='X',
        default=HOST,
        help='specify * to listen for requests from all ip addresses')
    a.add_argument(
        '--port', metavar='X',
        default=find_open_port(PORT),
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
        '--root-uri', metavar='X',
        default='',
        help='specify root uri for all routes')
    a.add_argument(
        '--origins', metavar='X', nargs='+', dest='allowed_origins',
        default=[],
        help='specify allowed origins')
    a.add_argument(
        '--disk-poll', metavar='X', type=int,
        default=DISK_POLL_IN_MILLISECONDS,
        help='interval in milliseconds to check disk for changes')
    a.add_argument(
        '--disk-debounce', metavar='X', type=int,
        default=DISK_DEBOUNCE_IN_MILLISECONDS,
        help='interval in milliseconds to wait until the disk stops changing')


def configure_serving_from(args):
    root_uri = args.root_uri
    if root_uri and not root_uri.startswith('/'):
        args.root_uri = '/' + root_uri


def serve_with(automation, args):
    return serve(
        automation,
        host=args.host,
        port=args.port,
        with_browser=args.with_browser,
        is_static=args.is_static,
        is_production=args.is_production,
        root_uri=args.root_uri,
        allowed_origins=args.allowed_origins,
        disk_poll_in_milliseconds=args.disk_poll,
        disk_debounce_in_milliseconds=args.disk_debounce)


def serve(
        automation,
        host=HOST,
        port=PORT,
        with_browser=True,
        is_static=False,
        is_production=False,
        root_uri='',
        allowed_origins=None,
        disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
        disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
    try:
        if with_browser and 'DISPLAY' in environ:
            L.info('opening browser; set --no-browser to disable')
            open_browser(f'http://localhost:{port}{root_uri}')
        automation.serve(
            host=host,
            port=port,
            is_static=is_static,
            is_production=is_production,
            root_uri=root_uri,
            allowed_origins=allowed_origins,
            disk_poll_in_milliseconds=disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds=disk_debounce_in_milliseconds)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


def check_port(port):
    if is_port_in_use(port):
        L.error('port %s is in use; could not start server', port)
        raise SystemExit


L = getLogger(__name__)


if __name__ == '__main__':
    do()

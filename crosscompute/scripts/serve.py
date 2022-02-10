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
    configure_logging_from(args)
    try:
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    serve_with(automation, args)


def configure_argument_parser_for_serving(a):
    a.add_argument(
        '--host', metavar='X',
        default=HOST,
        help='specify * to listen for requests from all ip addresses')
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
    return serve(
        automation,
        args.host,
        args.port,
        args.base_uri,
        args.with_browser,
        args.is_static,
        args.is_production,
        args.disk_poll,
        args.disk_debounce)


def serve(
        automation, host=HOST, port=PORT, base_uri='', with_browser=True,
        is_static=False, is_production=False,
        disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
        disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
    try:
        if is_port_in_use(port):
            raise CrossComputeError(
                f'port {port} is in use; cannot start server')
        if with_browser and 'DISPLAY' in environ:
            L.info('opening browser; set --no-browser to disable')
            open_browser(f'http://localhost:{port}{base_uri}')
        automation.serve(
            host=host,
            port=port,
            is_static=is_static,
            is_production=is_production,
            disk_poll_in_milliseconds=disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds=disk_debounce_in_milliseconds,
            base_uri=base_uri)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


L = getLogger(__name__)


if __name__ == '__main__':
    do()

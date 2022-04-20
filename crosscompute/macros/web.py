import socket
import webbrowser
from logging import getLogger
from random import randint
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import urlopen as open_uri

from markdown import markdown

from ..constants import MAXIMUM_PORT, MINIMUM_PORT
from .process import LoggableProcess


def escape_quotes_html(x):
    try:
        x = x.replace('"', '&#34;').replace("'", '&#39;')
    except AttributeError:
        pass
    return x


def escape_quotes_js(x):
    try:
        x = x.replace('"', '\\"').replace("'", "\\'")
    except AttributeError:
        pass
    return x


def get_html_from_markdown(text):
    html = markdown(text)
    clipped_html = html[3:-4]
    if '<p>' not in clipped_html and '</p>' not in clipped_html:
        html = html.removeprefix('<p>')
        html = html.removesuffix('</p>')
    return html


def find_open_port(
        default_port=None,
        minimum_port=MINIMUM_PORT,
        maximum_port=MAXIMUM_PORT):

    def get_new_port():
        return randint(minimum_port, maximum_port)

    port = default_port or get_new_port()
    port_count = maximum_port - minimum_port + 1
    closed_ports = set()
    while True:
        if not is_port_in_use(port):
            break
        closed_ports.add(port)
        if len(closed_ports) == port_count:
            raise OSError(
                'could not find an open port in '
                f'[{minimum_port}, {maximum_port}]')
        port = get_new_port()
    return port


def is_port_in_use(port):
    # https://stackoverflow.com/a/52872579
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        is_in_use = s.connect_ex(('127.0.0.1', int(port))) == 0
    return is_in_use


def open_browser(uri, check_interval_in_seconds=1):

    def wait_then_run():
        try:
            while True:
                try:
                    open_uri(uri)
                except HTTPError as e:
                    L.error(e)
                    return
                except URLError:
                    sleep(check_interval_in_seconds)
                else:
                    break
            webbrowser.open(uri)
        except KeyboardInterrupt:
            pass

    process = LoggableProcess(name='browser', target=wait_then_run)
    process.daemon = True
    process.start()


L = getLogger(__name__)

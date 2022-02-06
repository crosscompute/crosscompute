import socket
import webbrowser
from invisibleroads_macros_text import normalize_key
from logging import getLogger
from markdown import markdown
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import urlopen as open_uri

from .process import LoggableProcess


def format_slug(text):
    return normalize_key(text, word_separator='-')


def get_html_from_markdown(text):
    html = markdown(text)
    if '</p>\n<p>' not in html:
        html = html.removeprefix('<p>')
        html = html.removesuffix('</p>')
    return html


def is_port_in_use(port):
    # https://stackoverflow.com/a/52872579
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', int(port))) == 0


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

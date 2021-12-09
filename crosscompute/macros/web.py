import socket
import webbrowser
from logging import getLogger
from multiprocessing import Process
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import urlopen as open_uri

from .text import normalize_key


L = getLogger(__name__)


def format_slug(text):
    return normalize_key(text, word_separator='-')


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

    p = Process(target=wait_then_run)
    p.start()


def is_port_in_use(port):
    # https://stackoverflow.com/a/52872579
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

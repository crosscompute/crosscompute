import webbrowser
from multiprocessing import Process
from time import sleep
from urllib.request import urlopen as open_uri

from .text import normalize_key


def format_slug(text):
    return normalize_key(text, word_separator='-')


def open_browser(uri):
    run_when_ready(lambda: open_uri(uri), lambda: webbrowser.open(uri))


def run_when_ready(check, run, check_interval_in_seconds=1):
    p = Process(target=wait_then_run, args=(
        check, run, check_interval_in_seconds))
    p.start()


def wait_then_run(check, run, check_interval_in_seconds=1):
    try:
        while True:
            try:
                check()
            except Exception:
                sleep(check_interval_in_seconds)
            else:
                break
        run()
    except KeyboardInterrupt:
        pass

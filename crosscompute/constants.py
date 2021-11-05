from os import getenv
from os.path import expanduser


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))
HOST = '127.0.0.1'
PORT = 7000

from os import getenv
from os.path import expanduser


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))

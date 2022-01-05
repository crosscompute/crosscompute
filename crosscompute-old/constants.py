from os import getenv
from os.path import expanduser


FOLDER = getenv('CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))
PING_INTERVAL_IN_SECONDS = 1
ID_LENGTH = 16


STREAMS_ROUTE = '/streams'
RUN_ROUTE = '/r/{run_slug}'
MODE_ROUTE = '/{mode_name}'
MODE_NAME_BY_LETTER = {_[0]: _ for _ in MODE_NAMES}
FILE_ROUTE = '/{variable_path}'

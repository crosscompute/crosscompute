import re
from enum import IntEnum
from pathlib import Path

from .macros.web import format_slug


class Error(IntEnum):

    CONFIGURATION_NOT_FOUND = -100
    COMMAND_NOT_FOUND = -10


PACKAGE_FOLDER = Path(__file__).parent
TEMPLATES_FOLDER = PACKAGE_FOLDER / 'templates'
ID_LENGTH = 16


AUTOMATION_NAME = 'Automation X'
AUTOMATION_VERSION = '0.0.0'
AUTOMATION_PATH = Path('automate.yml')


HOST = '127.0.0.1'
PORT = 7000
DISK_POLL_IN_MILLISECONDS = 1000
DISK_DEBOUNCE_IN_MILLISECONDS = 1000


AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
VARIABLE_ROUTE = '/{variable_id}'
MODE_ROUTE = '/{mode_code}'
RUN_ROUTE = '/r/{run_slug}'
STYLE_ROUTE = '/s/{style_name}.css'
MUTATION_ROUTE = '/mutations{uri}.json'


MODE_NAMES = 'input', 'output', 'log', 'debug'
MODE_NAME_BY_CODE = {_[0]: _ for _ in MODE_NAMES}
MODE_CODE_BY_NAME = {k: v for v, k in MODE_NAME_BY_CODE.items()}
MINIMUM_PING_INTERVAL_IN_SECONDS = 1
MAXIMUM_PING_INTERVAL_IN_SECONDS = 30
MAXIMUM_MUTATION_AGE_IN_SECONDS = 60


FUNCTION_BY_NAME = {
    'slug': format_slug,
    'title': str.title,
}
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')
MAXIMUM_FILE_CACHE_LENGTH = 256

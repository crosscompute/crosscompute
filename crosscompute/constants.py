import re
from enum import IntEnum
from os import getenv
from pathlib import Path


class Error(IntEnum):

    CONFIGURATION_NOT_FOUND = -100
    COMMAND_NOT_RUNNABLE = -10


class Status(IntEnum):

    NEW = 0
    FAILED = -1
    DONE = 100


PACKAGE_FOLDER = Path(__file__).parent
TEMPLATES_FOLDER = PACKAGE_FOLDER / 'templates'
IMAGES_FOLDER = PACKAGE_FOLDER / 'images'
ID_LENGTH = 32
TOKEN_LENGTH = 32


AUTOMATION_NAME = 'Automation X'
AUTOMATION_VERSION = '0.0.0'
AUTOMATION_PATH = Path('automate.yml')


HOST = '127.0.0.1'
PORT = 7000
DISK_POLL_IN_MILLISECONDS = 1000
DISK_DEBOUNCE_IN_MILLISECONDS = 1000


AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
RUN_ROUTE = '/r/{run_slug}'
MODE_ROUTE = '/{mode_code}'
VARIABLE_ROUTE = '/{variable_id}'
STYLE_ROUTE = '/s/{style_name}.css'
MUTATION_ROUTE = '/mutations{uri}.json'


MODE_NAMES = 'input', 'output', 'log', 'debug'
MODE_NAME_BY_CODE = {_[0]: _ for _ in MODE_NAMES}
MODE_CODE_BY_NAME = {k: v for v, k in MODE_NAME_BY_CODE.items()}
MINIMUM_PING_INTERVAL_IN_SECONDS = 1
MAXIMUM_PING_INTERVAL_IN_SECONDS = 30
MAXIMUM_MUTATION_AGE_IN_SECONDS = 60


VARIABLE_ID_PATTERN = re.compile(r'[a-zA-Z0-9-_ ]+$')
VARIABLE_ID_TEMPLATE_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')
CACHED_FILE_SIZE_LIMIT_IN_BYTES = 1024
MAXIMUM_FILE_CACHE_LENGTH = 256


PRINTER_BY_NAME = {}
VIEW_BY_NAME = {}


MINIMUM_PORT = int(getenv('CROSSCOMPUTE_MINIMUM_PORT', 1024))
MAXIMUM_PORT = int(getenv('CROSSCOMPUTE_MAXIMUM_PORT', 65535))
PROXY_URI = getenv('CROSSCOMPUTE_PROXY_URI', '')


DEBUG_VARIABLE_DICTIONARIES = [{
    'id': 'execution_time_in_seconds',
    'view': 'number',
    'path': 'variables.dictionary',
}, {
    'id': 'return_code',
    'view': 'number',
    'path': 'variables.dictionary',
}]

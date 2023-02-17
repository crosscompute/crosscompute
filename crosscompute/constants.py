import re
from enum import IntEnum
from os import getenv
from pathlib import Path


class Error(IntEnum):

    CONFIGURATION_NOT_FOUND = -100
    COMMAND_NOT_RUNNABLE = -10
    COMMAND_INTERRUPTED = -1


class Status(IntEnum):

    NEW = 0
    FAILED = -1
    DONE = 100


PACKAGE_FOLDER = Path(__file__).parent
ASSETS_FOLDER = PACKAGE_FOLDER / 'assets'
TEMPLATE_PATH_BY_ID = {
    'base': str(ASSETS_FOLDER / 'base.html'),
    'live': str(ASSETS_FOLDER / 'live.html'),
    'root': str(ASSETS_FOLDER / 'root.html'),
    'automation': str(ASSETS_FOLDER / 'automation.html'),
    'batch': str(ASSETS_FOLDER / 'batch.html'),
    'step': str(ASSETS_FOLDER / 'step.html')}


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
STEP_ROUTE = '/{step_code}'
VARIABLE_ROUTE = '/{variable_id}'
STYLE_ROUTE = '/s/{style_name}.css'
MUTATION_ROUTE = '/mutations{uri}.json'
PORT_ROUTE = '/ports{uri}'


PACKAGE_MANAGER_NAMES = 'apt', 'dnf', 'npm', 'pip'
DESIGN_NAMES_BY_PAGE_ID = {
    'automation': ['input', 'output', 'none'],
    'input': ['flex-vertical', 'none'],
    'output': ['flex-vertical', 'none'],
    'log': ['flex-vertical', 'none'],
    'debug': ['flex-vertical', 'none'],
}
BUTTON_TEXT_BY_ID = {'run': 'Run'}


INTERVAL_UNIT_NAMES = 'seconds', 'minutes', 'hours', 'days', 'weeks'
STEP_NAMES = 'input', 'output', 'log', 'debug'
STEP_NAME_BY_CODE = {_[0]: _ for _ in STEP_NAMES}
STEP_CODE_BY_NAME = {k: v for v, k in STEP_NAME_BY_CODE.items()}
MINIMUM_PING_INTERVAL_IN_SECONDS = 1
MAXIMUM_PING_INTERVAL_IN_SECONDS = 30
MAXIMUM_MUTATION_AGE_IN_SECONDS = 180


VARIABLE_ID_PATTERN = re.compile(r'[a-zA-Z0-9-_ ]+$')
VARIABLE_ID_TEMPLATE_PATTERN = re.compile(r'{ *([a-zA-Z0-9-_| ]+?) *}')
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
    'path': 'variables.dictionary'}]

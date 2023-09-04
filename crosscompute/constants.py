import re
from datetime import datetime
from enum import IntEnum
from logging import WARNING
from os import getenv
from pathlib import Path


class Status(IntEnum):

    NEW = 0
    FAILED = -1
    DONE = 100


class Error(IntEnum):

    CONFIGURATION_NOT_FOUND = -100
    IMAGE_NOT_RUNNABLE = -20
    COMMAND_NOT_RUNNABLE = -10
    COMMAND_INTERRUPTED = -1


class Info:

    CONFIGURATION = 'c'
    SCRIPT = 'f'
    DATASET = 'd'
    VARIABLE = 'v'
    TEMPLATE = 't'
    STYLE = 's'


class Task:

    RUN_PRINT = 'r'
    PRINT_ONLY = 'p'


PACKAGE_FOLDER = Path(__file__).parent
ASSETS_FOLDER = PACKAGE_FOLDER / 'assets'
TEMPLATE_PATH_BY_ID = {
    'base': str(ASSETS_FOLDER / 'base.html'),
    'live': str(ASSETS_FOLDER / 'live.html'),
    'root': str(ASSETS_FOLDER / 'root.html'),
    'automation': str(ASSETS_FOLDER / 'automation.html'),
    'batch': str(ASSETS_FOLDER / 'batch.html'),
    'step': str(ASSETS_FOLDER / 'step.html')}
CACHE_FOLDER = Path('~/.crosscompute').expanduser()
FILES_FOLDER = CACHE_FOLDER / 'files'


ID_LENGTH = 32
TOKEN_LENGTH = 32


AUTOMATION_NAME = 'Automation X'
AUTOMATION_VERSION = '0.0.0'
AUTOMATION_PATH = Path('automate.yml')
COPYRIGHT_NAME = 'CrossCompute'
COPYRIGHT_URI = 'https://crosscompute.com'
COPYRIGHT_YEAR = datetime.now().year
ATTRIBUTION_TEXT = '''
[<img src="/assets/logo.svg" alt="{copyright_name}" loading="lazy">](
{copyright_uri}) © {copyright_year}. Made with the [CrossCompute Analytics
Software Development Kit](https://docs.crosscompute.com).
'''.strip()
LOGO_PATH = ASSETS_FOLDER / 'LogoBrand-Horizontal-20230501.svg'


HOST = '127.0.0.1'
PORT = 7000
DISK_DEBOUNCE_IN_MILLISECONDS = 1600
DISK_STEP_IN_MILLISECONDS = 50


VARIABLE_ROUTE = '/{variable_id}'
FILES_ROUTE = '/files.json'
STREAM_ROUTE = '/streams'
STYLE_ROUTE = '/assets/{style_name}.css'
MUTATION_ROUTE = '/mutations{uri}.json'
PORT_ROUTE = '/ports{uri}'


PRINTER_NAMES = 'pdf',


PACKAGE_MANAGER_NAMES = 'apt', 'dnf', 'npm', 'pip'
BUTTON_TEXT_BY_ID = {
    'back': 'Back',
    'continue': 'Continue'}


INTERVAL_UNIT_NAMES = 'seconds', 'minutes', 'hours', 'days', 'weeks'
STEP_CODE_BY_NAME = {k: v for v, k in STEP_NAME_BY_CODE.items()}
MAXIMUM_MUTATION_AGE_IN_SECONDS = 180


VARIABLE_ID_WHITELIST_PATTERN = re.compile(r'{ *(ROOT_URI) *}')


MINIMUM_PORT = int(getenv('CROSSCOMPUTE_MINIMUM_PORT', 1024))
MAXIMUM_PORT = int(getenv('CROSSCOMPUTE_MAXIMUM_PORT', 65535))
PROXY_URI = getenv('CROSSCOMPUTE_PROXY_URI', '')


DEBUG_VARIABLE_DICTIONARIES = [{
    'id': 'source_time',
    'view': 'number',
    'path': 'variables.dictionary',
}, {
    'id': 'execution_time_in_seconds',
    'view': 'number',
    'path': 'variables.dictionary',
}, {
    'id': 'return_code',
    'view': 'number',
    'path': 'variables.dictionary'}]


LOGGING_TIMESTAMP = '%Y%m%d-%H%M%S'
LOGGING_LEVEL_BY_PACKAGE_NAME = {
    'watchfiles': WARNING}

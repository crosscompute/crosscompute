import re
from os import getenv
from os.path import expanduser

from . import __version__
from .macros import format_slug


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))


HOST = '127.0.0.1'
PORT = 7000
DISK_POLL_IN_MILLISECONDS = 1000
DISK_DEBOUNCE_IN_MILLISECONDS = 1000
# PING_INTERVAL_IN_SECONDS = 20


HOME_ROUTE = '/'
STYLE_ROUTE = HOME_ROUTE + 's/{style_path}'
ECHOES_ROUTE = HOME_ROUTE + 'echoes'
AUTOMATION_ROUTE = HOME_ROUTE + 'a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
PAGE_ROUTE = '/{page_type}'
FILE_ROUTE = '/{variable_path}'


CONFIGURATION_EXTENSIONS = '.yaml', '.yml', '.toml', '.ini', '.cfg'
TEMPLATE_EXTENSIONS = '.md', '.ipynb'


PAGE_TYPE_NAMES = 'input', 'output', 'log', 'debug'
PAGE_TYPE_NAME_BY_LETTER = {_[0]: _ for _ in PAGE_TYPE_NAMES}
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')
FUNCTION_BY_NAME = {'slug': format_slug, 'title': str.title}


VARIABLE_CACHE = {}


AUTOMATION_NAME = 'Automation X'
AUTOMATION_VERSION = '0.0.0'
CONFIGURATION_PATH = 'automate.yml'
CONFIGURATION = {
    'crosscompute': __version__,
    'name': 'name of your automation',
    'version': '0.0.0',
}

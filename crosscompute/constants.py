import re
from os import getenv
from os.path import expanduser

from .macros import format_slug


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))


HOST = '127.0.0.1'
PORT = 7000


HOME_ROUTE = '/'
STYLE_ROUTE = HOME_ROUTE + 's/{style_path}'
ECHOES_ROUTE = HOME_ROUTE + 'echoes'
AUTOMATION_ROUTE = HOME_ROUTE + 'a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
PAGE_ROUTE = '/{page_type}'
FILE_ROUTE = '/{variable_path}'


CONFIGURATION_EXTENSIONS = '.yaml', '.yml', '.toml', '.ini', '.cfg'
TEMPLATE_EXTENSIONS = '.md', '.ipynb'


AUTOMATION_NAME = 'Automation {automation_index}'
PAGE_TYPE_NAMES = 'input', 'output', 'log', 'debug'
PAGE_TYPE_NAME_BY_LETTER = {_[0]: _ for _ in PAGE_TYPE_NAMES}
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')
FUNCTION_BY_NAME = {'slug': format_slug}

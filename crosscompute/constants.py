import re
from os.path import dirname, join

from .macros.web import format_slug


PACKAGE_FOLDER = dirname(__file__)
TEMPLATES_FOLDER = join(PACKAGE_FOLDER, 'templates')


AUTOMATION_NAME = 'Automation X'
AUTOMATION_VERSION = '0.0.0'
AUTOMATION_PATH = 'automate.yml'


HOST = '127.0.0.1'
PORT = 7000
DISK_POLL_IN_MILLISECONDS = 1000
DISK_DEBOUNCE_IN_MILLISECONDS = 1000
CONFIGURATION_EXTENSIONS = '.yaml', '.yml', '.toml', '.ini', '.cfg'
STYLE_EXTENSIONS = '.css',
# TEMPLATE_EXTENSIONS = '.md', '.ipynb'


AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
STYLE_ROUTE = '/s/{style_name}'
MODE_NAMES = 'input', 'output', 'log', 'debug'


FUNCTION_BY_NAME = {
    'slug': format_slug,
    'title': str.title,
}
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')
VARIABLE_CACHE = {}

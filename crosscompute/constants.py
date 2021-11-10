import re
from os import getenv
from os.path import expanduser


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))


HOST = '127.0.0.1'
PORT = 7000


HOME_ROUTE = '/'
STYLE_ROUTE = HOME_ROUTE + '{style_path}'
ECHOES_ROUTE = HOME_ROUTE + 'echoes'
AUTOMATION_ROUTE = HOME_ROUTE + 'a/{automation_slug}'
BATCH_ROUTE = HOME_ROUTE + 'b/{batch_slug}'
REPORT_ROUTE = HOME_ROUTE + '{variable_type}'
FILE_ROUTE = HOME_ROUTE + '{variable_path}'


CONFIGURATION_EXTENSIONS = '.yaml', '.yml', '.toml', '.ini', '.cfg'
TEMPLATE_EXTENSIONS = '.md', '.ipynb'


AUTOMATION_NAME = 'Automation {automation_index}'
VARIABLE_TYPE_NAMES = 'input', 'output', 'log', 'debug'
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')

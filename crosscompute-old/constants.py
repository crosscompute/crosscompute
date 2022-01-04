import re
from os import getenv
from os.path import expanduser


FOLDER = getenv('CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))
PING_INTERVAL_IN_SECONDS = 1
ID_LENGTH = 16


STYLE_ROUTE = '/s/{style_hash}'
STREAMS_ROUTE = '/streams'
AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
RUN_ROUTE = '/r/{run_slug}'
MODE_ROUTE = '/{mode_name}'
MODE_NAMES = 'input', 'output', 'log', 'debug'
MODE_NAME_BY_LETTER = {_[0]: _ for _ in MODE_NAMES}
FILE_ROUTE = '/{variable_path}'


CONFIGURATION_EXTENSIONS = '.yaml', '.yml', '.toml', '.ini', '.cfg'
STYLE_EXTENSIONS = '.css',
TEMPLATE_EXTENSIONS = '.md', '.ipynb'
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')

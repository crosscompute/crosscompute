from os import getenv
from os.path import expanduser


FOLDER = getenv(
    'CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))


HOST = '127.0.0.1'
PORT = 7000


HOME_ROUTE = '/'
STYLE_ROUTE = '/style.css'
ECHOES_ROUTE = '/echoes'
AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
REPORT_ROUTE = '/{variable_type}'
FILE_ROUTE = '/{variable_path}'


AUTOMATION_CONFIGURATION_EXTENSIONS = [
    '.yaml',
    '.yml',
    '.toml',
    '.ini',
    '.cfg',
]
AUTOMATION_NAME = 'Automation {automation_index}'

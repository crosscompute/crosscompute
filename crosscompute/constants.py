from invisibleroads_macros_log import get_log


VERSION = '0.8.4'


CLIENT_URL = 'https://crosscompute.com'
SERVER_URL = 'https://services.crosscompute.com'


AUTOMATION_FILE_NAME = 'automation.yml'
TOOL_FILE_NAME = 'tool.yml'
RESULT_FILE_NAME = 'result.yml'


# TODO: Load supported views from server
VIEW_NAMES = [
    'text',
    'number',
    'markdown',
    'table',
    'image',
    'map',
]
DEFAULT_VIEW_NAME = 'text'


L = get_log('crosscompute')

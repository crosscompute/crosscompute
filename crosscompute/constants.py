from invisibleroads_macros_log import get_log


L = get_log(__name__.split('.')[0])


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
DEFAULT_HOST = 'https://services.crosscompute.com'


AUTOMATION_FILE_NAME = 'automation.yml'
TOOL_FILE_NAME = 'tool.yml'
RESULT_FILE_NAME = 'result.yml'

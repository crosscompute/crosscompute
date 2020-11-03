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
CLIENT_URL = 'https://services.crosscompute.com'
SERVER_URL = 'https://services.crosscompute.com'

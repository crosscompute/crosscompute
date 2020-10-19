from invisibleroads_macros_log import get_log


L = get_log(__name__.split('.')[0])


# TODO: Load supported views from server
VIEW_NAMES = [
    'text',
    'number',
    'markdown',
    'table',
    'map',
]
DEFAULT_VIEW_NAME = 'text'
DEFAULT_HOST = 'https://services.crosscompute.com'

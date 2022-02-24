from invisibleroads_macros_log import get_log
from os.path import expanduser


# TODO: Load supported views from server
VIEW_NAMES = [
    'text',
    'number',
    'markdown',
    'table',
    'image',
    'map',
    'electricity-network',
    'file',
]
DEFAULT_VIEW_NAME = 'text'


PRINT_FORMAT_NAMES = [
    'pdf'
]


DEBUG_VARIABLE_DEFINITIONS = [{
    'id': 'stdout',
    'name': 'Standard Output',
    'view': 'text',
    'path': 'stdout.txt',
}, {
    'id': 'stderr',
    'name': 'Standard Error',
    'view': 'text',
    'path': 'stderr.txt',
}]

import re
from invisibleroads_macros_log import get_log


HOST = 'https://services.projects.crosscompute.com'


L = get_log(__name__.split('.')[0])


VARIABLE_TEXT_PATTERN = re.compile(r'({[^}]+})')
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')

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


FUNCTION_BY_NAME = {
    'slug': format_slug,
    'title': str.title,
}
VARIABLE_CACHE = {}

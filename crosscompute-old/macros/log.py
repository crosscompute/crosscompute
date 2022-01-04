import os
import re
from os.path import expanduser


HOME_FOLDER_SHORT_PATH = '%UserProfile%' if os.name == 'nt' else '~'


def format_path(x):
    return re.sub(r'^' + expanduser('~'), HOME_FOLDER_SHORT_PATH, x)

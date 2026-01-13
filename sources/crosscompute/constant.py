from enum import Enum
from pathlib import Path


class ToolAccess(Enum):
    PRIVATE = 0
    PROTECTED = 2
    HIDDEN = 5
    PUBLIC = 7


USER_SETTINGS_PATH = '~/.crosscompute/user.yaml'
DATA_FOLDER = '~/.crosscompute'
LOG_PATH = DATA_FOLDER + '/logs/user.log'


PACKAGE_FOLDER = Path(__file__).parent
ASSET_FOLDER = PACKAGE_FOLDER / 'asset'

from pathlib import Path


USER_SETTINGS_PATH = '~/.crosscompute/user.yaml'
DATA_FOLDER = '~/.crosscompute'
LOG_PATH = DATA_FOLDER + '/logs/user.log'


PACKAGE_FOLDER = Path(__file__).parent
ASSET_FOLDER = PACKAGE_FOLDER / 'asset'

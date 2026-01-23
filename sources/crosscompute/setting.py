from pathlib import Path

from crosscompute_macros.abstract import Mold
from crosscompute_macros.datetime import (
    get_datestamp)
from crosscompute_macros.yaml import (
    sync_load_raw_yaml)
from crosscompute_validation.error import (
    CrossComputeError)

from .constant import (
    ASSET_FOLDER,
    DATA_FOLDER,
    LOG_PATH,
    USER_SETTINGS_PATH)


def get_settings_path(default_path=USER_SETTINGS_PATH):
    default_path = Path(default_path).expanduser()
    asset_path = ASSET_FOLDER / 'configuration' / 'user.yaml'
    try:
        if default_path.exists():
            path = default_path
        elif asset_path.exists():
            path = asset_path
        else:
            x = 'settings path was not found'
            raise CrossComputeError(x)
    except OSError as e:
        x = 'settings path is not accessible'
        raise CrossComputeError(x) from e
    return path


def load_settings_from_path(settings_path=None, overrides_map=None):
    if not settings_path:
        settings_path = get_settings_path()
    if not overrides_map:
        overrides_map = {}
    d = sync_load_raw_yaml(settings_path)
    load_settings_from_map(d | overrides_map)
    D = declared_settings
    D.settings_path = settings_path


def load_settings_from_map(d):
    D = declared_settings
    D.set('data_folder', d, expand_path)
    D.set('log_path', d, expand_path)
    D.set('server_uri', d)
    D.set('mode', d)
    # Worker
    D.set('worker_slug', d)
    # User
    D.set('user_token', d)
    # Extended
    compute_extended_settings()


def expand_path(path):
    if path:
        D = declared_settings
        kwargs = {'date_stamp': date_stamp}
        if hasattr(D, 'data_folder'):
            kwargs['data_folder'] = D.data_folder
        path = Path(str(path).format(**kwargs)).expanduser()
    return path


def compute_extended_settings():
    D = declared_settings
    data_folder = D.data_folder

    E = extended_settings
    # E.payloads_folder = data_folder / 'payloads'


declared_settings = Mold({
    'data_folder': DATA_FOLDER,
    'log_path': LOG_PATH,
    'server_uri': 'https://crosscompute.com',
    'mode': 'production',
    # Worker
    'worker_slug': None,
    # User
    'user_token': None})
extended_settings = Mold()


date_stamp = get_datestamp()

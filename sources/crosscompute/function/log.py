from logging.config import dictConfig as configure_logging_from_map
from pathlib import Path

from ruamel.yaml import YAML

from ..setting import (
    declared_settings as D)
from .asset import (
    asset_storage)


def configure_log():
    log_config = load_log_configuration()
    for handler_map in log_config['handlers'].values():
        if 'filename' in handler_map:
            log_path = handler_map['filename']
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    configure_logging_from_map(log_config)


def load_log_configuration():
    if D.mode == 'development':
        configuration_name = 'development.yaml'
        value_by_key = {}
    else:
        configuration_name = 'production.yaml'
        log_path = Path(D.log_path).expanduser()
        value_by_key = {
            'default_log_path': log_path,
            'access_log_path': log_path}
    text = asset_storage.load_string_text(
        f'configuration/{configuration_name}')
    return YAML(typ='safe').load(text.substitute(value_by_key))

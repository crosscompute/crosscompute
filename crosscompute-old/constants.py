from os.path import expanduser


FOLDER = getenv('CROSSCOMPUTE_FOLDER', expanduser('~/.crosscompute'))
PING_INTERVAL_IN_SECONDS = 1


MODE_NAME_BY_LETTER = {_[0]: _ for _ in MODE_NAMES}

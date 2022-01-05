from invisibleroads_macros_disk import get_file_hash
from os.path import abspath


def has_changed(path, hash_by_path):
    absolute_path = abspath(path)
    if absolute_path not in hash_by_path:
        return False
    file_hash = get_file_hash(absolute_path)
    if file_hash == hash_by_path[absolute_path]:
        return False
    hash_by_path[absolute_path] = file_hash
    return True


def get_hash_by_path(paths):
    return {abspath(_): get_file_hash(_) for _ in paths}

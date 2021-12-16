from hashlib import blake2b
from os import makedirs
from os.path import realpath


CHUNK_SIZE_IN_BYTES = 2 ** 13


def make_folder(folder):
    try:
        makedirs(folder)
    except FileExistsError:
        pass
    return folder


def is_path_in_folder(path, folder, normalize=realpath):
    normalized_path = normalize(path)
    normalized_folder = normalize(folder)
    return normalized_path.startswith(normalized_folder)


def make_file_hash(path):
    with open(path, 'rb') as f:
        file_hash = blake2b(usedforsecurity=False)
        while chunk := f.read(CHUNK_SIZE_IN_BYTES):
            file_hash.update(chunk)
    return file_hash.hexdigest()

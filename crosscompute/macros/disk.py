from os import makedirs
from os.path import realpath


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

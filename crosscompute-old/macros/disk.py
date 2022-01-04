from invisibleroads_macros_security import make_random_string
from os import makedirs
from os.path import join, realpath


def make_folder(folder):
    try:
        makedirs(folder)
    except FileExistsError:
        pass
    return folder


def make_unique_folder(parent_folder, name_length):
    while True:
        folder_name = make_random_string(name_length)
        folder = join(parent_folder, folder_name)
        try:
            makedirs(folder)
        except FileExistsError:
            pass
        else:
            break
    return folder


def is_path_in_folder(path, folder, normalize=realpath):
    normalized_path = normalize(path)
    normalized_folder = normalize(folder)
    return normalized_path.startswith(normalized_folder)

from os import makedirs


def make_folder(folder):
    try:
        makedirs(folder)
    except FileExistsError:
        pass
    return folder

from os.path import getmtime

from .iterable import LRUDict


class FileCache(LRUDict):

    def __init__(self, *args, load_file_data, maximum_length: int, **kwargs):
        super().__init__(*args, maximum_length=maximum_length, **kwargs)
        self._load_file_data = load_file_data

    def __getitem__(self, path):
        if path in self:
            file_time, file_data = super().__getitem__(path)
            if getmtime(path) == file_time:
                return file_data
        file_data = self._load_file_data(path)
        self.__setitem__(path, file_data)
        return file_data

    def __setitem__(self, path, data):
        value = (getmtime(path), data)
        super().__setitem__(path, value)

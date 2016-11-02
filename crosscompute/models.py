from invisibleroads_macros.database import DummyBase, FolderMixin
from os.path import join


class Result(FolderMixin, DummyBase):

    __tablename__ = 'result'

    def get_source_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'x')

    def get_target_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'y')

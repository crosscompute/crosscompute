from invisibleroads_posts.models import DummyBase, FolderMixin
from os.path import join


class Tool(FolderMixin, DummyBase):

    id = 1

    @property
    def name(self):
        return self.title

    @classmethod
    def get_from(Class, request, record_id=None):
        return Class(id=record_id or Class.id)


class Result(FolderMixin, DummyBase):

    tool = Tool()
    tool_id = Tool.id

    @property
    def name(self):
        return self.id[:5]

    def get_source_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'x')

    def get_target_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'y')

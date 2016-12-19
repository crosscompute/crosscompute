from invisibleroads_posts.models import DummyBase, FolderMixin
from os.path import join


class Tool(FolderMixin, DummyBase):

    id = 1

    @classmethod
    def get_from(Class, request):
        return Class()


class Result(FolderMixin, DummyBase):

    tool_id = Tool.id

    @classmethod
    def get_from(Class, request):
        instance = super(Result, Class).get_from(request)
        instance.tool = Tool()
        return instance

    def get_source_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'x')

    def get_target_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'y')

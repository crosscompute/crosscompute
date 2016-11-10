from invisibleroads_macros.database import DummyBase, FolderMixin
from os.path import join


TOOL_ID = 1


class Tool(FolderMixin, DummyBase):

    __tablename__ = 'tool'

    @classmethod
    def get_from(Class, request):
        settings = request.registry.settings
        tool = Class(id=TOOL_ID)
        tool.definition = settings['tool_definition']
        return tool


class Result(FolderMixin, DummyBase):

    __tablename__ = 'result'

    @classmethod
    def get_from(Class, request):
        instance = super(Result, Class).get_from(request)
        instance.tool_id = TOOL_ID
        return instance

    def get_source_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'x')

    def get_target_folder(self, data_folder):
        return join(self.get_folder(data_folder), 'y')

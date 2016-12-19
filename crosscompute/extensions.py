from abc import ABCMeta
from os import sep as folder_separator
from os.path import splitext
from six import add_metaclass

from .configurations import find_tool_definition


@add_metaclass(ABCMeta)
class ToolExtension(object):

    @classmethod
    def prepare_tool_definition(self, path):
        pass


class DefaultTool(ToolExtension):

    @classmethod
    def prepare_tool_definition(self, path):
        if path:
            path = path.rstrip(folder_separator)
            path = path.replace('_', '-')
            path = splitext(path)[0]
        return find_tool_definition(tool_name=path)

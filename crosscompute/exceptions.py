class CrossComputeError(Exception):
    pass


class DataTypeError(CrossComputeError):
    pass


class DataParseError(CrossComputeError):

    def __init__(self, message_by_name, value_by_key):
        self.message_by_name = message_by_name
        self.value_by_key = value_by_key
        self.args = (message_by_name,)


class ToolConfigurationNotFound(CrossComputeError):
    pass


class ToolDependencyError(CrossComputeError):
    pass


class ToolNotFound(CrossComputeError):
    pass


class ToolNotSpecified(CrossComputeError):
    pass

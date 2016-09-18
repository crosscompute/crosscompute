class CrossComputeError(Exception):
    pass


class DataTypeError(CrossComputeError):
    pass


class ToolConfigurationNotFound(CrossComputeError):
    pass


class ToolDependencyError(CrossComputeError):
    pass


class ToolNotFound(CrossComputeError):
    pass


class ToolNotSpecified(CrossComputeError):
    pass

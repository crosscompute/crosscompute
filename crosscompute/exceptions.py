class CrossComputeError(Exception):
    pass


class DataTypeError(CrossComputeError):
    pass


class DependencyError(CrossComputeError):
    pass


class ToolConfigurationNotFound(CrossComputeError):
    pass


class ToolNotFound(CrossComputeError):
    pass


class ToolNotSpecified(CrossComputeError):
    pass

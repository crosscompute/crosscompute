class CrossComputeError(Exception):
    pass


class ConfigurationNotFound(CrossComputeError):
    pass


class DependencyError(CrossComputeError):
    pass


class ToolNotFound(CrossComputeError):
    pass


class ToolNotSpecified(CrossComputeError):
    pass

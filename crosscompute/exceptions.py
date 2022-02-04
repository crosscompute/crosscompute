class CrossComputeError(Exception):
    pass


class CrossComputeConfigurationError(CrossComputeError):
    pass


class CrossComputeConfigurationNotFoundError(CrossComputeConfigurationError):
    pass


class CrossComputeDataError(CrossComputeError):
    pass

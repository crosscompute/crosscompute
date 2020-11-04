from pyramid.httpexceptions import HTTPBadRequest


class CrossComputeError(Exception):
    pass


class CrossComputeDefinitionError(HTTPBadRequest, CrossComputeError):
    pass


class CrossComputeExecutionError(HTTPBadRequest, CrossComputeError):
    pass

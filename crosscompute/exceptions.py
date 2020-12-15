from pyramid.httpexceptions import HTTPBadRequest, HTTPInternalServerError


class CrossComputeError(Exception):
    pass


class CrossComputeConnectionError(HTTPInternalServerError, CrossComputeError):
    pass


class CrossComputeDefinitionError(HTTPBadRequest, CrossComputeError):
    pass


class CrossComputeExecutionError(HTTPBadRequest, CrossComputeError):
    pass


class CrossComputeImplementationError(
        HTTPInternalServerError, CrossComputeError):
    pass


class CrossComputeKeyboardInterrupt(KeyboardInterrupt, CrossComputeError):
    pass

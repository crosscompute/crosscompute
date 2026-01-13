from crosscompute_validation.error import (
    CrossComputeError)


class RepositoryCloneError(CrossComputeError):

    def __init__(self, repository_uri):
        super().__init__(f'download failed for repository "{repository_uri}"')


class RepositoryCheckoutError(CrossComputeError):

    def __init__(self, repository_uri, commit_hash):
        super().__init__(
            f'checkout "{commit_hash}" failed for repository '
            f'"{repository_uri}"')

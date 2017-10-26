import os
from contextlib import contextmanager


ENVIRONMENT_VARIABLES = os.environ.copy()


if os.name == 'nt':

    COMMAND_LINE_JOIN = '^'
    SCRIPT_EXTENSION = '.bat'
    ENVIRONMENT_VARIABLES['PYTHONIOENCODING'] = 'utf-8'

    def prepare_path_argument(path):
        return path.replace('\\', '\\\\')

else:

    COMMAND_LINE_JOIN = '\\'
    SCRIPT_EXTENSION = '.sh'

    def prepare_path_argument(path):
        return path


try:
    from contextlib import suppress
except ImportError:
    @contextmanager
    def suppress(*exceptions):
        try:
            yield
        except exceptions:
            pass


try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess  # noqa

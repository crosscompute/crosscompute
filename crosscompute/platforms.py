import os


SCRIPT_ENVIRONMENT = os.environ.copy()


if os.name == 'nt':

    COMMAND_LINE_JOIN = '^'
    SCRIPT_EXTENSION = '.bat'
    SCRIPT_ENVIRONMENT['PYTHONIOENCODING'] = 'utf-8'

    def prepare_path_argument(path):
        return path.replace('\\', '\\\\')

else:

    COMMAND_LINE_JOIN = '\\'
    SCRIPT_EXTENSION = '.sh'

    def prepare_path_argument(path):
        return path

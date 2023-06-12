# TODO: Move all functions to macros
from logging import (
    basicConfig,
    getLogger,
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING)

from ..constants import (
    LOGGING_TIMESTAMP)


def configure_argument_parser_for_logging(argument_parser):
    argument_parser.add_argument(
        '--quiet', '-q', dest='quietness', action='count', default=0,
        help='decrease logging level; stack as -qq')
    argument_parser.add_argument(
        '--verbose', '-v', dest='verbosity', action='count', default=0,
        help='increase logging level; stack as -vv')
    argument_parser.add_argument(
        '--timestamp', metavar='X', default=LOGGING_TIMESTAMP,
        help='customize logging timestamp format')


def configure_logging_from(args):
    # TODO: Keep in routines
    configure_logging(args.verbosity - args.quietness, args.timestamp)


def configure_logging(intensity, timestamp):
    # TODO: Make default be warning
    # TODO: Set jupyterlab-crosscompute to -v for INFO
    logging_format = '%(asctime)s %(levelname)s %(message)s'
    if intensity >= 1:
        logging_level = DEBUG
        logging_format = (
            '%(asctime)s %(levelname)s %(module)s.%(funcName)s:%(lineno)s '
            '%(message)s')
    elif intensity == 0:
        logging_level = INFO
    elif intensity == -1:
        logging_level = WARNING
    elif intensity == -2:
        logging_level = ERROR
    elif intensity < -2:
        logging_level = CRITICAL
    basicConfig(
        format=logging_format, datefmt=timestamp, level=logging_level)
    # TODO: Move this into configure_logging_from
    if logging_level >= DEBUG:
        getLogger('watchfiles').setLevel(ERROR)

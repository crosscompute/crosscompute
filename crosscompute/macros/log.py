from logging import (
    basicConfig,
    getLogger,
    DEBUG,
    INFO,
    WARNING)


def configure_argument_parser_for_logging(argument_parser):
    argument_parser.add_argument(
        '--debug', dest='with_debug', action='store_true', default=False,
        help='show debugging messages')


def configure_logging_from(args, package_names=None):
    with_debug = args.with_debug
    configure_logging(with_debug, '%Y%m%d-%H%M%S')
    if not with_debug:
        for package_name in package_names:
            getLogger(package_name).setLevel(WARNING)


def configure_logging(with_debug, timestamp):
    if with_debug:
        logging_level = DEBUG
        logging_format = (
            '%(asctime)s %(levelname)s %(module)s.%(funcName)s:%(lineno)s '
            '%(message)s')
    else:
        logging_level = INFO
        logging_format = '%(asctime)s %(levelname)s %(message)s'
    basicConfig(format=logging_format, datefmt=timestamp, level=logging_level)

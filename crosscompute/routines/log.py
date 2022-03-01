import logging


def configure_argument_parser_for_logging(argument_parser):
    argument_parser.add_argument(
        '--quiet', '-q', dest='quietness', action='count', default=0,
        help='decrease logging level; stack as -qq')
    argument_parser.add_argument(
        '--verbose', '-v', dest='verbosity', action='count', default=0,
        help='increase logging level; stack as -vv')


def configure_logging_from(args):
    configure_logging(args.verbosity - args.quietness)


def configure_logging(intensity):
    logging_format = '%(asctime)s %(levelname)s %(message)s'
    if intensity >= 1:
        logging_level = logging.DEBUG
        logging_format = (
            '%(asctime)s %(levelname)s %(module)s.%(funcName)s:%(lineno)s '
            '%(message)s')
    elif intensity == 0:
        logging_level = logging.INFO
    elif intensity == -1:
        logging_level = logging.WARNING
    elif intensity == -2:
        logging_level = logging.ERROR
    elif intensity <= -2:
        logging_level = logging.CRITICAL
    logging.basicConfig(
        format=logging_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging_level)

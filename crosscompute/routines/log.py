import logging


def configure_argument_parser_for_logging(argument_parser):
    argument_parser.add_argument(
        '--verbose', '-v', dest='verbosity', action='count', default=0)


def configure_logging(verbosity):
    if verbosity == 0:
        logging_level = logging.ERROR
    elif verbosity == 1:
        logging_level = logging.WARNING
    elif verbosity == 2:
        logging_level = logging.INFO
    else:
        logging_level = logging.DEBUG
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging_level)

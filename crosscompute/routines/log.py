import logging


def configure_argument_parser_for_logging(argument_parser):
    argument_parser.add_argument(
        '--quiet', '-q', dest='quietness', action='count', default=0)
    argument_parser.add_argument(
        '--verbose', '-v', dest='verbosity', action='count', default=0)


def configure_logging_from(args):
    configure_logging(args.verbosity - args.quietness)


def configure_logging(intensity):
    if intensity == 0:
        logging_level = logging.INFO
    elif intensity < -1:
        logging_level = logging.CRITICAL
    elif intensity == -1:
        logging_level = logging.ERROR
    elif intensity == +1:
        logging_level = logging.WARNING
    elif intensity > +1:
        logging_level = logging.DEBUG
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging_level)

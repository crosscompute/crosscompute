from argparse import ArgumentParser
from logging import getLogger

from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.routines.automation import (
    DiskAutomation,
    get_script_engine)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    engine = get_script_engine(args.engine_name, args.with_rebuild)
    run_with(automation, engine, args)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--engine', metavar='X', dest='engine_name',
        choices={'unsafe', 'podman'},
        help='specify engine used to run scripts')
    a.add_argument(
        '--no-rebuild', dest='with_rebuild', action='store_false',
        help='do not rebuild batches and container images')


def run_with(automation, engine, args):
    return run(automation, engine)


def run(automation, engine):
    try:
        engine.run_configuration(automation)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


L = getLogger(__name__)


if __name__ == '__main__':
    do()

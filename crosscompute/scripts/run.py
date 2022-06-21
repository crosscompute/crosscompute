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
        configure_running_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
    except CrossComputeError as e:
        L.error(e)
        return
    run_with(automation, args)


def configure_argument_parser_for_running(a):
    a.add_argument(
        '--engine', metavar='X',
        default='unsafe', choices={'unsafe', 'podman'},
        help='specify engine used to run scripts')
    '''
    a.add_argument(
        '--images', metavar='X', nargs='+', dest='allowed_images',
        default=[],
        help='specify allowed images')
    '''


def configure_running_from(args):
    engine_name = args.engine
    if engine_name == 'unsafe':
        L.warning(
            'using engine=unsafe; use engine=podman for untrusted code')


def run_with(automation, args):
    return run(
        automation,
        engine_name=args.engine)


def run(
        automation,
        engine_name='unsafe'):
    script_engine = get_script_engine(engine_name)
    try:
        script_engine.run_configuration(automation)
    except CrossComputeError as e:
        L.error(e)
    except KeyboardInterrupt:
        pass


L = getLogger(__name__)


if __name__ == '__main__':
    do()

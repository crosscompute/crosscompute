import inspect
import sys
from argparse import RawDescriptionHelpFormatter
from invisibleroads.scripts import LoggingScript, launch_script

from .. import __description__
from ..exceptions import CrossComputeError
from ..routines import get_bash_configuration_text, render_object


class OutputtingScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--json', action='store_true', dest='as_json',
            help='render output as json')


def launch(argv=sys.argv):
    launch_script(
        'crosscompute',
        argv,
        description=__description__,
        epilogue=get_bash_configuration_text(),
        formatter_class=RawDescriptionHelpFormatter)


def run_safely(function, arguments, is_quiet=False, as_json=False):
    kwargs = {}
    function_parameters = inspect.signature(function).parameters
    for key in ['is_quiet', 'as_json']:
        if key not in function_parameters:
            continue
        kwargs[key] = locals()[key]
    try:
        d = function(*arguments, **kwargs)
    except CrossComputeError as e:
        sys.exit(1 if is_quiet else render_object(e.args[0], as_json))
    if not is_quiet:
        print(render_object(d, as_json))
    return d

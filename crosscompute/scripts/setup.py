try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
from invisibleroads.scripts import Script

from . import prepare_tool_definition
from ..exceptions import ToolDependencyError


class SetupScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')
        argument_subparser.add_argument(
            '--upgrade', '-U', action='store_true',
            help='upgrade dependencies')

    def run(self, args):
        tool_definition = prepare_tool_definition(args.tool_name)
        try:
            install_dependencies(tool_definition, args.upgrade)
        except ToolDependencyError as e:
            exit(e)


def install_dependencies(tool_definition, upgrade=False):
    install_python_dependencies(
        tool_definition.get('python.dependencies'), upgrade)


def install_python_dependencies(python_dependencies, upgrade=False):
    if not python_dependencies:
        return
    command_terms = ['pip', 'install']
    if upgrade:
        command_terms.append('-U')
    try:
        subprocess.check_call(command_terms + python_dependencies)
    except subprocess.CalledProcessError:
        raise ToolDependencyError(
            'Could not install dependencies (%s)' % ', '.join(
                python_dependencies))

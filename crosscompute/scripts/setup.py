try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
from invisibleroads.scripts import Script

from . import load_tool_definition
from ..exceptions import DependencyError


class SetupScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')
        argument_subparser.add_argument(
            '--upgrade', '-U', action='store_true',
            help='upgrade dependencies')

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        try:
            install_dependencies(tool_definition, args.upgrade)
        except DependencyError as e:
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
        raise DependencyError('Dependencies not installed (%s).' % ', '.join(
            python_dependencies))

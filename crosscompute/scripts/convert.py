import codecs
import nbconvert
import nbformat
import shutil
import tempfile
from collections import OrderedDict
from crosscompute.configurations import RESERVED_ARGUMENT_NAMES
from os import chdir
from os.path import basename, join, splitext

from ..exceptions import CrossComputeError


def prepare_tool_from_notebook(notebook_path):
    notebook_name = splitext(basename(notebook_path))[0]
    notebook = load_notebook(notebook_path)
    script_folder = prepare_script_folder(
        tempfile.mkdtemp(), notebook, notebook_name)
    chdir(script_folder)
    return notebook_name


def load_notebook(notebook_path):
    for version in sorted(nbformat.versions, reverse=True):
        try:
            return nbformat.read(notebook_path, as_version=version)
            break
        except Exception:
            pass
    else:
        raise CrossComputeError


def prepare_script_folder(target_folder, notebook, notebook_name):
    tool_arguments = load_tool_arguments(notebook)
    # Prepare paths
    for k, v in tool_arguments.items():
        if k.endswith('_path'):
            shutil.copy(v, target_folder)
    # Prepare command-line script
    script_lines = []
    script_lines.append('from sys import argv')
    script_lines.append('%s = argv[1:]' % ', '.join(tool_arguments))
    notebook.cells[0]['source'] = '\n'.join(script_lines)
    script_content, script_info = nbconvert.export_script(notebook)
    script_name = 'run' + script_info['output_extension']
    if script_name.endswith('.py'):
        command_name = 'python'
    else:
        raise CrossComputeError
    # Save script
    script_path = join(target_folder, script_name)
    codecs.open(script_path, 'w', encoding='utf-8').write(script_content)
    # Save configuration
    configuration_path = join(target_folder, 'cc.ini')
    configuration_lines = []
    configuration_lines.append('[crosscompute %s]' % notebook_name)
    configuration_lines.append('command_template = %s %s %s' % (
        command_name, script_name,
        ' '.join('{%s}' % x for x in tool_arguments).strip()))
    for k, v in tool_arguments.items():
        if k in RESERVED_ARGUMENT_NAMES:
            continue
        configuration_lines.append('%s = %s' % (k, v))
    codecs.open(configuration_path, 'w', encoding='utf-8').write(
        '\n'.join(configuration_lines).strip())
    return target_folder


def load_tool_arguments(notebook):
    g, l = OrderedDict(), OrderedDict()
    block_content = notebook['cells'][0]['source']
    exec(block_content, g, l)
    return l

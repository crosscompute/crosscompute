'''
import webbrowser
import yaml
from collections import defaultdict
from markdown import markdown
from os import listdir
from os.path import splitext
from waitress import serve


    configuration_paths_by_format = get_configuration_paths_by_format()
    for (
        configuration_format,
        configuration_paths,
    ) in configuration_paths_by_format.items():
        if configuration_format != 'yaml':
            continue
        configuration = yaml.safe_load(open(configuration_path, 'rt'))
        if 'crosscompute' not in configuration:
            continue
        # TODO: Assert version
        break

    display_layout = configuration['display']['layout']

    webbrowser.open('http://localhost:8000')

    # check if configuration file exists
    # if not, create one
    # if it does exist, launch server
    # make default configuration
    # render default configuration to yaml, ini, toml


def get_configuration_paths_by_format(configuration_folder='.'):
    configuration_paths_by_format = defaultdict(list)
    for path in listdir(configuration_folder):
        root, extension = splitext(path)
        if extension in ['.cfg', '.ini']:
            configuration_format = 'ini'
        elif extension == '.toml':
            configuration_format = 'toml'
        elif extension in ['.yaml', '.yml']:
            configuration_format = 'yaml'
        else:
            continue
        configuration_paths_by_format[configuration_format].append(path)
    return dict(configuration_paths_by_format)
'''

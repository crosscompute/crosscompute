# TODO: Load existing configuration
from argparse import ArgumentParser
from invisibleroads_macros_log import format_path
from logging import getLogger
from os.path import exists, isdir, join

from crosscompute import __version__
from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_PATH,
    AUTOMATION_VERSION,
    TEMPLATES_FOLDER)
from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.routines.automation import Automation
from crosscompute.routines.configuration import (
    get_configuration_format,
    load_raw_configuration_yaml,
    save_raw_configuration_yaml)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def do():
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    args = a.parse_args()
    configure_logging_from(args)

    configure_with(args)


def configure_argument_parser_for_configuring(a):
    a.add_argument(
        'path_or_folder', nargs='?',
        default='.',
        help='configuration path or folder')


def configure_with(args):
    path_or_folder = args.path_or_folder
    if exists(path_or_folder):
        try:
            automation = Automation.load(path_or_folder)
            configuration = automation.configuration
        except CrossComputeError:
            configuration = {}
    configuration, configuration_path = input_configuration_with(
        configuration, args)
    del configuration['folder']
    del configuration['path']
    print(dict(configuration))
    save_configuration(configuration_path, configuration)
    return configuration_path


def input_configuration_with(configuration, args):
    if not configuration:
        configuration = load_raw_configuration_yaml(join(
            TEMPLATES_FOLDER, 'configuration.yaml'), with_comments=True)
    old_automation_name = configuration.get('name', AUTOMATION_NAME)
    old_automation_version = configuration.get('version', AUTOMATION_VERSION)
    old_configuration_path = get_configuration_path(args.path_or_folder)
    try:
        new_automation_name = input(
            'automation name [%s]: ' % old_automation_name)
        new_automation_version = input(
            'automation version [%s]: ' % old_automation_version)
        new_configuration_path = input(
            'configuration path [%s]: ' % format_path(old_configuration_path))
    except KeyboardInterrupt:
        print()
        raise SystemExit
    configuration['crosscompute'] = __version__
    configuration['name'] = new_automation_name or old_automation_name
    configuration['version'] = new_automation_version or old_automation_version
    return configuration, new_configuration_path or old_configuration_path


def save_configuration(configuration_path, configuration):
    if exists(configuration_path):
        L.warning(f'{format_path(configuration_path)} already exists')
        question = '\033[1moverwrite? yes or [no]:\033[0m '
        participle = 'overwritten'
    else:
        question = 'save? yes or [no]: '
        participle = 'saved'
    if not input(question).lower() == 'yes':
        L.warning(f'{format_path(configuration_path)} not {participle}')
        raise SystemExit
    try:
        configuration_format = get_configuration_format(configuration_path)
        save_raw_configuration = {
            'yaml': save_raw_configuration_yaml,
        }[configuration_format]
        save_raw_configuration(configuration_path, configuration)
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    L.info(f'{format_path(configuration_path)} {participle}')


def get_configuration_path(path_or_folder):
    if path_or_folder and isdir(path_or_folder):
        configuration_path = join(path_or_folder, AUTOMATION_PATH)
    else:
        configuration_path = path_or_folder or AUTOMATION_PATH
    return configuration_path


L = getLogger(__name__)


if __name__ == '__main__':
    do()

from argparse import ArgumentParser
from invisibleroads_macros_log import format_path
from logging import getLogger
from pathlib import Path

from crosscompute import __version__
from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_PATH,
    AUTOMATION_VERSION,
    TEMPLATES_FOLDER)
from crosscompute.exceptions import (
    CrossComputeError)
from crosscompute.routines.configuration import (
    load_raw_configuration,
    save_raw_configuration)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
    except CrossComputeError as e:
        L.error(e)
        return

    configure_with(args)


def configure_argument_parser_for_configuring(a):
    a.add_argument(
        'path_or_folder', nargs='?',
        default='.',
        help='configuration path or folder')


def configure_with(args):
    return configure(args.path_or_folder)


def configure(path_or_folder):
    configuration = {}
    path_or_folder = Path(path_or_folder)
    if path_or_folder.exists():
        try:
            configuration = load_raw_configuration(
                path_or_folder, with_comments=True)
        except CrossComputeError:
            pass
    configuration, configuration_path = input_configuration(
        configuration, path_or_folder)
    print(dict(configuration))
    save_configuration(configuration_path, configuration)
    return configuration_path


def input_configuration(configuration, path_or_folder):
    if not configuration:
        configuration = load_raw_configuration(
            TEMPLATES_FOLDER / 'configuration.yml', with_comments=True)
    old_automation_name = configuration.get('name', AUTOMATION_NAME)
    old_automation_version = configuration.get('version', AUTOMATION_VERSION)
    old_configuration_path = get_configuration_path(path_or_folder)
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
    configuration_path = Path(new_configuration_path or old_configuration_path)
    return configuration, configuration_path


def save_configuration(configuration_path, configuration):
    formatted_configuration_path = format_path(configuration_path)
    if configuration_path.exists():
        L.warning('%s already exists', formatted_configuration_path)
        question = '\033[1moverwrite? yes or [no]:\033[0m '
        participle = 'overwritten'
    else:
        question = 'save? yes or [no]: '
        participle = 'saved'
    if not input(question).lower() == 'yes':
        L.warning('%s not %s', formatted_configuration_path, participle)
        raise SystemExit
    try:
        save_raw_configuration(configuration_path, configuration)
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    L.info('%s %s', formatted_configuration_path, participle)


def get_configuration_path(path_or_folder):
    if path_or_folder and path_or_folder.is_dir():
        configuration_path = path_or_folder / AUTOMATION_PATH
    else:
        configuration_path = path_or_folder or AUTOMATION_PATH
    return configuration_path


L = getLogger(__name__)


if __name__ == '__main__':
    do()

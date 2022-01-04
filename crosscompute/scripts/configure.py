from argparse import ArgumentParser
from logging import getLogger
from os.path import exists, isdir, join

from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_PATH,
    AUTOMATION_VERSION,
    TEMPLATES_FOLDER)
from crosscompute.exceptions import (
    CrossComputeError)
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
        'path_or_folder',
        nargs='?',
        help='configuration path or folder')


def configure_with(args):
    configuration, configuration_path = input_configuration_with(args)
    print(dict(configuration))
    save_configuration(configuration_path, configuration)
    return configuration_path


def input_configuration_with(args):
    automation_path = get_automation_path(args.path_or_folder)
    try:
        automation_name = input(
            'automation_name [%s]: ' % AUTOMATION_NAME)
        automation_version = input(
            'automation_version [%s]: ' % AUTOMATION_VERSION)
        configuration_path = input(
            'configuration_path [%s]: ' % automation_path)
    except KeyboardInterrupt:
        print()
        raise SystemExit
    configuration = load_raw_configuration_yaml(join(
        TEMPLATES_FOLDER, 'configuration.yaml'), with_comments=True)
    configuration['name'] = automation_name or AUTOMATION_NAME
    configuration['version'] = automation_version or AUTOMATION_VERSION
    return configuration, configuration_path or automation_path


def save_configuration(configuration_path, configuration):
    if exists(configuration_path):
        L.warning(f'{configuration_path} already exists')
        question = '\033[1moverwrite? yes or [no]:\033[0m '
        participle = 'overwritten'
    else:
        question = 'save? yes or [no]: '
        participle = 'saved'
    if not input(question).lower() == 'yes':
        L.warning(f'{configuration_path} not {participle}')
        raise SystemExit
    try:
        configuration_format = get_configuration_format(configuration_path)
    except CrossComputeError as e:
        L.error(e)
        raise SystemExit
    save_raw_configuration = {
        'yaml': save_raw_configuration_yaml,
    }[configuration_format]
    save_raw_configuration(configuration_path, configuration)
    L.info(f'{configuration_path} {participle}')


def get_automation_path(path_or_folder):
    if path_or_folder and isdir(path_or_folder):
        automation_path = join(path_or_folder, AUTOMATION_PATH)
    else:
        automation_path = path_or_folder or AUTOMATION_PATH
    return automation_path


L = getLogger(__name__)


if __name__ == '__main__':
    do()

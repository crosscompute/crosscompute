import logging
import yaml
from argparse import ArgumentParser
from os.path import exists, isdir, join

from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_VERSION,
    CONFIGURATION,
    CONFIGURATION_PATH)
from crosscompute.exceptions import CrossComputeError
from crosscompute.routines.configuration import (
    get_configuration_format)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)


def configure_argument_parser_for_configuring(a):
    a.add_argument(
        'path_or_folder',
        nargs='?',
        help='automation configuration path or folder')


def configure_with(args):
    path_or_folder = args.path_or_folder
    if path_or_folder and isdir(path_or_folder):
        automation_path = join(path_or_folder, CONFIGURATION_PATH)
    else:
        automation_path = path_or_folder or CONFIGURATION_PATH
    configuration = CONFIGURATION.copy()

    try:
        automation_name = input(
            'automation_name [%s]: ' % AUTOMATION_NAME)
        automation_version = input(
            'automation_version [%s]: ' % AUTOMATION_VERSION)
        configuration_path = input(
            'configuration_path [%s]: ' % automation_path)
    except KeyboardInterrupt:
        print()
        exit()

    configuration['name'] = automation_name or AUTOMATION_NAME
    configuration['version'] = automation_version or AUTOMATION_VERSION
    configuration_path = configuration_path or automation_path

    print()
    print(configuration)
    print()

    if exists(configuration_path):
        logging.warning(f'{configuration_path} already exists')
        should_overwrite = input(
            '\033[1moverwrite? yes or [no]:\033[0m ').lower() == 'yes'
        print()
        if not should_overwrite:
            logging.warning(f'{configuration_path} not overwritten')
            exit()
    else:
        should_save = input('save? yes or [no]: ').lower() == 'yes'
        print()
        if not should_save:
            logging.warning(f'{configuration_path} not saved')
            exit()

    try:
        configuration_format = get_configuration_format(configuration_path)
    except CrossComputeError as e:
        logging.error(e)
        exit()
    if configuration_format == 'yaml':
        yaml.dump(configuration, open(configuration_path, 'wt'))
    logging.info(f'{configuration_path} saved')

    return configuration_path


def do():
    a = ArgumentParser()
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_logging(a)
    args = a.parse_args()
    configure_logging_from(args)

    configure_with(args)


if __name__ == '__main__':
    do()

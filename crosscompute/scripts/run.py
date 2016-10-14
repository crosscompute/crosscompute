from argparse import ArgumentParser, SUPPRESS
from invisibleroads_macros.configuration import unicode_safely
from os.path import abspath
from sys import argv

from ..exceptions import DataParseError
from ..types import (
    parse_data_dictionary_from, DATA_TYPE_BY_SUFFIX, RESERVED_ARGUMENT_NAMES)
from . import ToolScript, prepare_target_folder, run_script


class RunScript(ToolScript):

    def configure(self, argument_subparser):
        super(RunScript, self).configure(argument_subparser)
        argument_subparser.add_argument(
            '--upgrade', action='store_true', help='upgrade dependencies')

    def run(self, args):
        tool_definition, data_folder = super(RunScript, self).run(args)
        tool_name = tool_definition['tool_name']
        argument_parser = ArgumentParser(tool_name)
        argument_parser.add_argument(
            'tool_name', nargs='?', help=SUPPRESS, type=unicode_safely)
        argument_parser.add_argument(
            '--target_folder', type=unicode_safely, metavar='FOLDER')
        argument_parser = configure_argument_parser(
            argument_parser, tool_definition)
        raw_arguments = argument_parser.parse_known_args(argv[2:])[0].__dict__
        try:
            result_arguments = parse_data_dictionary_from({
                k: raw_arguments[k] for k in tool_definition['argument_names']
            }, tool_definition['configuration_folder'])
        except DataParseError as e:
            return [(k + '.error', v) for k, v in e.message_by_name.items()]
        target_folder = raw_arguments.get(
            'target_folder') or prepare_target_folder(data_folder)
        run_script(abspath(target_folder), tool_definition, result_arguments)


def configure_argument_parser(argument_parser, tool_definition):
    for x in tool_definition['argument_names']:
        if x in RESERVED_ARGUMENT_NAMES:
            continue
        d = {}
        if x in tool_definition:
            d['default'] = tool_definition[x]
        else:
            d['required'] = True
        for suffix in DATA_TYPE_BY_SUFFIX:
            if x.endswith('_' + suffix):
                d['metavar'] = suffix.upper()
                break
        else:
            if x.endswith('_folder'):
                d['metavar'] = 'FOLDER'
            elif x.endswith('_path'):
                d['metavar'] = 'PATH'
        argument_parser.add_argument('--' + x, type=unicode_safely, **d)
    return argument_parser

import tempfile
from argparse import ArgumentParser, SUPPRESS
from invisibleroads.scripts import Script
from os.path import join
from sys import argv

from ..configurations import RESERVED_ARGUMENT_NAMES
from ..exceptions import DataTypeError
from ..types import get_data_type_by_suffix, get_result_arguments
from . import load_tool_definition, prepare_result_response_folder, run_script


class RunScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')
        argument_subparser.add_argument('--data_folder', metavar='FOLDER')

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        tool_name = tool_definition['tool_name']
        data_folder = args.data_folder or join(
            tempfile.gettempdir(), 'crosscompute', tool_name)
        data_type_by_suffix = get_data_type_by_suffix()
        argument_parser = ArgumentParser(tool_name)
        argument_parser.add_argument('tool_name', nargs='?', help=SUPPRESS)
        argument_parser = configure_argument_parser(
            argument_parser, tool_definition, data_type_by_suffix)
        raw_arguments = argument_parser.parse_args(argv[2:]).__dict__
        try:
            result_arguments = get_result_arguments(
                tool_definition, raw_arguments, data_type_by_suffix,
                data_folder)
        except DataTypeError as e:
            return [(k + '.error', v) for k, v in e.args]
        target_folder = result_arguments.get(
            'target_folder') or prepare_result_response_folder(data_folder)[1]
        run_script(
            target_folder, tool_definition, result_arguments,
            data_type_by_suffix)


def configure_argument_parser(
        argument_parser, tool_definition, data_type_by_suffix):
    for x in tool_definition['argument_names']:
        d = {}
        if x in tool_definition:
            d['default'] = tool_definition[x]
        elif x not in RESERVED_ARGUMENT_NAMES:
            d['required'] = True
        for suffix in data_type_by_suffix:
            if x.endswith('_' + suffix):
                d['metavar'] = suffix.upper()
                break
        else:
            if x.endswith('_folder'):
                d['metavar'] = 'FOLDER'
            elif x.endswith('_path'):
                d['metavar'] = 'PATH'
        argument_parser.add_argument('--' + x, **d)
    return argument_parser

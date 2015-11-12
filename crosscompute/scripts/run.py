import sys
from argparse import ArgumentParser, SUPPRESS
from invisibleroads.scripts import Script
from invisibleroads_macros.disk import make_enumerated_folder
from os.path import join, sep

from ..configurations import RESERVED_ARGUMENT_NAMES
from ..types import get_data_type_packs, get_result_arguments
from . import load_tool_definition, run_script


class RunScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('tool_name', nargs='?')

    def run(self, args):
        tool_definition = load_tool_definition(args.tool_name)
        tool_name = tool_definition['tool_name']
        data_type_packs = get_data_type_packs()
        data_folder = join(sep, 'tmp', tool_name)
        argument_parser = ArgumentParser(tool_name)
        argument_parser.add_argument('tool_name', nargs='?', help=SUPPRESS)
        argument_parser = configure_argument_parser(
            argument_parser, tool_definition, data_type_packs)
        try:
            result_arguments = get_result_arguments(
                tool_definition['argument_names'],
                argument_parser.parse_args(sys.argv[2:]).__dict__,
                data_type_packs, data_folder)
        except TypeError as e:
            return {'errors': dict(e.args)}
        run_script(
            result_arguments.get('target_folder') or make_enumerated_folder(
                join(data_folder, 'results')),
            tool_definition, result_arguments, data_type_packs, debug=True)


def configure_argument_parser(
        argument_parser, tool_definition, data_type_packs):
    for x in tool_definition['argument_names']:
        d = {}
        if x + '.value' in tool_definition:
            d['default'] = tool_definition[x + '.value']
        elif x not in RESERVED_ARGUMENT_NAMES:
            d['required'] = True
        for name, extension in data_type_packs:
            if x.endswith('_' + name):
                d['metavar'] = name.upper()
                break
        else:
            if x.endswith('_folder'):
                d['metavar'] = 'FOLDER'
            elif x.endswith('_path'):
                d['metavar'] = 'PATH'
        argument_parser.add_argument('--' + x, **d)
    return argument_parser

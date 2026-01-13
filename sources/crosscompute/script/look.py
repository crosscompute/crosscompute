#!/usr/bin/env python3
import asyncio
import sys
from argparse import ArgumentParser
from logging import getLogger

from crosscompute_macros.error import (
    MacroError)
from crosscompute_macros.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute_validation.error import (
    CrossComputeError)
from crosscompute_validation.function.configuration import (
    load_configuration)


async def start(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_looking(a)
    args = a.parse_args(arguments)
    configure_logging_from(args, {})
    configuration = await look_with(args)
    for tool_definition in configuration.tool_definitions:
        L.info(tool_definition.slug)


async def look_with(args):
    return await look(args.path_or_folder)


async def look(path_or_folder):
    return await load_configuration(path_or_folder)


def configure_argument_parser_for_looking(a):
    a.add_argument(
        'path_or_folder', nargs='?',
        default='.',
        help='configuration path or folder')


L = getLogger('crosscompute.scripts.look')


if __name__ == '__main__':
    try:
        asyncio.run(start())
    except (MacroError, CrossComputeError) as e:
        L.error(e)
        sys.exit(1)

#!/usr/bin/env python3
import asyncio
from argparse import ArgumentParser
from logging import getLogger
import sys

from crosscompute_macros.error import (
    MacroError)
from crosscompute_validation.error import (
    CrossComputeError)

from crosscompute.script.add import (
    configure_argument_parser_for_adding,
    add_with)
from crosscompute.script.look import (
    configure_argument_parser_for_looking,
    look_with)


def run():
    try:
        asyncio.run(start())
    except (MacroError, CrossComputeError) as e:
        L.error(e)
        sys.exit(1)


async def start(arguments=None):
    a = ArgumentParser()
    s = a.add_subparsers(dest='command_name')
    configure_argument_parser_for_looking(s.add_parser('look'))
    configure_argument_parser_for_adding(s.add_parser('add'))
    args = a.parse_args(arguments)
    command_name = args.command_name
    match command_name:
        case 'look':
            await look_with(args)
        case 'draft':
            pass
        case 'run':
            pass
        case 'serve':
            pass
        case 'print':
            pass
        case 'add':
            await add_with(args)
        case 'work':
            pass
        case 'clean':
            pass


L = getLogger('crosscomputes.scripts.launch')


if __name__ == '__main__':
    run()

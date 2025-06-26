import asyncio
from argparse import ArgumentParser
from logging import getLogger

from crosscompute.scripts.add import (
    add_with)


def run():
    asyncio.run(start())


async def start(arguments=None):
    args = get_args(arguments)
    command_names = args.command_names
    match primary_command_name := command_names[0]:
        case 'info':
            pass
        case 'configure':
            pass
        case 'run':
            pass
        case 'serve':
            pass
        case 'print':
            pass
        case 'add':
            await add_with(args, command_names[1:])
        case 'work':
            pass
        case _:
            L.error(
                '"%s" is not a recognized command. %s',
                primary_command_name, COMMANDS_OVERVIEW_TEXT)


def get_args(arguments):
    a = ArgumentParser()
    configure_argument_parser_for_launching(a)
    args = a.parse_args(arguments)
    return args


def configure_argument_parser_for_launching(a):
    a.add_argument('command_names', nargs='+')


COMMANDS_OVERVIEW_TEXT = '''\
Here are the available commands:

crosscompute info
crosscompute configure
crosscompute run
crosscompute serve
crosscompute print
crosscompute add
crosscompute work'''
L = getLogger('crosscomputes.scripts.launch')


if __name__ == '__main__':
    run()

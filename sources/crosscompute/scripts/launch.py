import asyncio
from argparse import ArgumentParser
from logging import getLogger

from crosscompute.scripts.add import (
    configure_argument_parser_for_adding,
    add_with)


def run():
    asyncio.run(start())


async def start(arguments=None):
    a = ArgumentParser()
    s = a.add_subparsers(dest='command_name')
    configure_argument_parser_for_adding(s.add_parser('add'))
    args = a.parse_args(arguments)
    command_name = args.command_name
    match command_name:
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
            await add_with(args)
        case 'work':
            pass


L = getLogger('crosscomputes.scripts.launch')


if __name__ == '__main__':
    run()

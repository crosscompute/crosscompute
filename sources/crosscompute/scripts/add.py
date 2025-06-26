import asyncio
from argparse import ArgumentParser
from logging import getLogger
from os import getenv


async def start(arguments=None):
    a = ArgumentParser()
    a.add_argument('configuration_uris', nargs='+')
    configure_argument_parser_for_adding(a)
    args = a.parse_args(arguments)
    await add_with(args)


def configure_argument_parser_for_adding(a):
    pass


async def add_with(args, configuration_uris):
    for configuration_uri in configuration_uris:
        if configuration_uri.startswith(('git@', 'https://github.com')):
            await add_repository_uri(args, configuration_uri)
        elif configuration_uri.startswith('http://github.com'):
            L.error('replace http://github.com with https://github.com')
        else:
            await add_repository_path(args, configuration_uri)


async def add_repository_uri(args, configuration_uri):
    pass


async def add_repository_path(args, configuration_path):
    pass


SERVER_URI = getenv('SERVER_URI')
USER_TOKEN = getenv('USER_TOKEN')
L = getLogger(__name__)


if __name__ == '__main__':
    asyncio.run(start())


# crosscompute add ~/Projects/crosscompute-examples/add-numbers
# crosscompute add git@github.com:crosscompute/crosscompute-examples/add-numbers
# crosscompute add https://github.com/crosscompute/crosscompute-examples/tree/0.9.5/add-numbers

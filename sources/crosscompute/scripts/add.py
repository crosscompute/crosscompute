import asyncio
from argparse import ArgumentParser
from os import getenv


async def start(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_adding(a)
    args = a.parse_args(arguments)
    await add_with(args)


def configure_argument_parser_for_adding(a):
    a.add_argument('configuration_uri')


async def add_with(args):
    print(args)


SERVER_URI = getenv('SERVER_URI')
USER_TOKEN = getenv('USER_TOKEN')


if __name__ == '__main__':
    asyncio.run(start())


# crosscompute add ~/Projects/crosscompute-examples/add-numbers
# crosscompute add git@github.com:crosscompute/crosscompute-examples/add-numbers
# crosscompute add https://github.com/crosscompute/crosscompute-examples/tree/0.9.5/add-numbers

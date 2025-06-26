import asyncio
from argparse import ArgumentParser
from logging import getLogger
from os import getenv
from pathlib import PurePath
from subprocess import CalledProcessError

from aiofiles.tempfile import TemporaryDirectory
from crosscompute_macros.process import (
    run_process)

from crosscompute.backends.base import (
    format_results)
from crosscompute.backends.cloud import (
    CloudBackend)
from crosscompute.backends.disk import (
    DiskBackend)
from crosscompute.errors import (
    RepositoryCheckoutError,
    RepositoryCloneError)
from crosscompute.functions.variable import (
    initialize_variable)


async def start(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_adding(a)
    args = a.parse_args(arguments)
    await add_with(args)


def configure_argument_parser_for_adding(a):
    a.add_argument('configuration_uri')
    a.add_argument('--commit_hash')
    a.add_argument('--configuration_path')


async def add_with(args):
    configuration_uri = args.configuration_uri
    if configuration_uri.startswith(('git@', 'https://github.com')):
        await add_repository_uri(args, configuration_uri)
    elif configuration_uri.startswith('http://github.com'):
        L.error('replace http://github.com with https://github.com')
    else:
        await add_repository_path(SERVER_URI, USER_TOKEN, configuration_uri)


async def add_repository_uri(args, repository_uri):
    commit_hash = args.commit_hash
    configuration_path = args.configuration_path
    async with TemporaryDirectory() as temporary_folder:
        repository_folder = PurePath(temporary_folder)
        await download_repository(
            repository_folder, repository_uri, commit_hash)
        repository_path = (
            repository_folder / configuration_path if configuration_path else
            repository_folder)
        await add_repository_path(SERVER_URI, USER_TOKEN, repository_path)
        await asyncio.sleep(60)


async def download_repository(target_folder, repository_uri, commit_hash):
    try:
        await run_process([
            'git', 'clone', '--recursive', '--quiet', '--depth', '1',
            repository_uri, str(target_folder),
        ], env={
            'GIT_ASKPASS': 'true',
            'SSH_AUTH_SOCK': SSH_AUTH_SOCK,
        }, check=True)
    except CalledProcessError as e:
        raise RepositoryCloneError(repository_uri) from e
    if not commit_hash:
        return
    try:
        await run_process([
            'git', 'remote', 'set-branches', 'origin', '*',
        ], cwd=target_folder, check=True)
        await run_process([
            'git', 'fetch', '-v', '--depth', '1',
        ], cwd=target_folder, check=True)
        await run_process([
            'git', 'checkout', commit_hash,
        ], cwd=target_folder, check=True)
    except CalledProcessError as e:
        raise RepositoryCheckoutError(repository_uri, commit_hash) from e


async def add_repository_path(server_uri, user_token, repository_path):
    initialize_variable()
    disk_backend = await DiskBackend.load(repository_path)
    tools = await disk_backend.get_tools()
    async with CloudBackend(server_uri, user_token) as cloud_backend:
        tools = await cloud_backend.save(tools)
        results = await cloud_backend.run(tools)
        results = await cloud_backend.wait(results)
    L.info(format_results(results))


SERVER_URI = getenv('SERVER_URI')
USER_TOKEN = getenv('USER_TOKEN')
SSH_AUTH_SOCK = getenv('SSH_AUTH_SOCK')
L = getLogger('crosscompute.scripts.add')


if __name__ == '__main__':
    asyncio.run(start())

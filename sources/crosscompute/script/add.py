#!/usr/bin/env python3
import asyncio
import subprocess
import sys
from argparse import (
    ArgumentParser,
    RawTextHelpFormatter)
from logging import getLogger
from os import getenv
from pathlib import Path
from urllib.parse import urlsplit as split_uri

from crosscompute_macros.datetime import (
    get_longstamp)
from crosscompute_macros.error import (
    MacroError)
from crosscompute_macros.process import (
    run_process)
from crosscompute_macros.text import (
    format_slug)
from crosscompute_macros.yaml import (
    load_raw_yaml)
from crosscompute_validation.error import (
    CrossComputeConfigurationError,
    CrossComputeError)

from crosscompute_platform.backend.base import (
    format_results)
from crosscompute_platform.backend.cloud import (
    CloudBackend)
from crosscompute_platform.backend.disk import (
    DiskBackend)
from crosscompute_platform.constant import (
    ToolAccess)
from crosscompute.error import (
    RepositoryCheckoutError,
    RepositoryCloneError)
from crosscompute.function.log import (
    configure_log)
from crosscompute_platform.function.variable import (
    initialize_variable)
from crosscompute.setting import (
    declared_settings as D,
    load_settings_from_path)


async def start(arguments=None):
    a = ArgumentParser(epilog=EPILOG, formatter_class=RawTextHelpFormatter)
    configure_argument_parser_for_adding(a)
    args = a.parse_args(arguments)
    await add_with(args)


def configure_argument_parser_for_adding(a):
    a.add_argument('configuration_path')
    a.add_argument('--tool')
    a.add_argument('--action')


async def add_with(args):
    load_settings_from_path()
    configure_log()
    initialize_variable()
    server_uri = getenv('SERVER_URI') or D.server_uri
    user_token = getenv('USER_TOKEN') or D.user_token
    worker_slug = getenv('WORKER_SLUG') or D.worker_slug
    configuration_path = args.configuration_path
    configuration = await load_raw_yaml(configuration_path)
    action = args.action
    tool_slug = args.tool
    tool_maps = configuration.get('tools', [])
    if tool_slug:
        tool_maps = [_ for _ in tool_maps if _['slug'] == tool_slug]
    tool_paths = await download_tools(tool_maps)
    tool_by_slug = await load_tools(tool_paths)
    tools = annotate_tools(tool_by_slug, tool_maps, worker_slug)
    await upload_tools(server_uri, user_token, tools, action)


async def download_tools(tool_maps):
    paths = []
    timestamp = get_longstamp()
    for tool_map in tool_maps:
        repository_map = tool_map['repository']
        repository_uri = repository_map['uri']
        commit_hash = repository_map['version']
        relative_path = repository_map['path']
        repository_folder = await get_repository_folder(
            REPOSITORIES_FOLDER, repository_uri, commit_hash, timestamp)
        paths.append(repository_folder / relative_path)
    return paths


async def load_tools(tool_paths):
    tool_by_slug = {}
    for path in tool_paths:
        L.info(f'loading {path}')
        disk_backend = await DiskBackend.load(path)
        for tool in await disk_backend.get_tools():
            slug = tool.slug
            if slug in tool_by_slug:
                x = f'tool already exists; slug="{slug}"; path="{path}"'
                raise CrossComputeConfigurationError(x)
            tool_by_slug[slug] = tool
    return tool_by_slug


def annotate_tools(tool_by_slug, tool_maps, worker_slug):
    for tool_map in tool_maps:
        slug = tool_map.pop('slug')
        try:
            tool = tool_by_slug[slug]
        except KeyError as e:
            x = f'tool was not found; slug="{slug}"'
            raise CrossComputeConfigurationError(x) from e

        compatibility = tool.compatibility
        workers = compatibility.get('workers', [])
        for worker in workers:
            if worker.get('slug') == worker_slug:
                break
        else:
            if worker_slug:
                workers.append({'slug': worker_slug})
        if workers:
            compatibility['workers'] = workers

        tool.environment = tool_map.get('environment', {})

        if 'visibility' in tool_map:
            tool_map['visibility'] = get_tool_access(tool_map['visibility'])
        if 'runnability' in tool_map:
            tool_map['runnability'] = get_tool_access(tool_map['runnability'])
        tool.details = tool_map
    return list(tool_by_slug.values())


async def upload_tools(server_uri, user_token, tools, action):
    async with CloudBackend(server_uri, user_token) as cloud_backend:
        await cloud_backend.ping()
        if action in [None, 'save']:
            tools = await cloud_backend.save(tools)
        if action in [None, 'run']:
            results = await cloud_backend.run(tools)
            results = await cloud_backend.wait(results)
            L.info(format_results(results))
        if action in [None, 'release']:
            tools = await cloud_backend.release(tools)


async def get_repository_folder(
        source_folder, repository_uri, commit_hash, timestamp):
    u = split_uri(repository_uri)
    base_hash = format_slug(u.netloc + u.path + '-' + commit_hash)
    base_folder = source_folder / base_hash
    try:
        repository_folder = list(base_folder.glob('*'))[-1]
        L.info(f'skipping download for {repository_uri}')
    except IndexError:
        repository_folder = base_folder / timestamp
        L.info(f'downloading {repository_uri} {commit_hash}')
        await download_repository(
            repository_folder, repository_uri, commit_hash)
    return Path(repository_folder)


async def download_repository(target_folder, repository_uri, commit_hash):
    try:
        await run_process([
            'git', 'clone', '--recursive', '--quiet', '--depth', '1',
            repository_uri, target_folder,
        ], env={
            'GIT_ASKPASS': 'true',
            'SSH_AUTH_SOCK': getenv('SSH_AUTH_SOCK'),
        }, check=True)
    except subprocess.CalledProcessError as e:
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
    except subprocess.CalledProcessError as e:
        raise RepositoryCheckoutError(repository_uri, commit_hash) from e


def get_tool_access(access_name):
    return ToolAccess[access_name.upper()].value


EPILOG = '''environment variables:
  SERVER_URI
  USER_TOKEN
  WORKER_SLUG'''
REPOSITORIES_FOLDER = Path('~/.cache/crosscompute/repositories').expanduser()
L = getLogger('crosscompute.scripts.add')


if __name__ == '__main__':
    try:
        asyncio.run(start())
    except (MacroError, CrossComputeError) as e:
        L.error(e)
        sys.exit(1)

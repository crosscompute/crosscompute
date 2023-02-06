from logging import getLogger, DEBUG, ERROR
from time import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from invisibleroads_macros_process import LoggableProcess, StoppableProcess
from invisibleroads_macros_web.starlette import ExtraResponseHeadersMiddleware
from watchgod import watch

from ..constants import HOST, PORT, TEMPLATE_PATH_BY_ID
from ..exceptions import CrossComputeError
from ..routers import automation, mutation, root, token
from ..settings import (
    site, template_environment, template_globals, template_path_by_id)
from .database import DiskDatabase
from .interface import Server


class DiskServer(Server):

    def __init__(
            self, environment, safe, queue, work, changes,
            host=HOST, port=PORT, with_restart=False, root_uri='',
            allowed_origins=None):
        self._environment = environment
        self._safe = safe
        self._queue = queue
        self._work = work
        self._changes = changes
        self._host = host
        self._port = port
        self._with_restart = with_restart
        self._root_uri = root_uri
        self._allowed_origins = allowed_origins

    def serve(self, configuration):
        LoggableProcess(
            name='worker', target=self._work, args=(self._queue,)).start()
        host, port, root_uri, with_restart, allowed_origins = [
            self._host, self._port, self._root_uri, self._with_restart,
            self._allowed_origins]
        self._refresh(configuration)
        app = get_app(root_uri)
        if with_restart:
            app.add_middleware(
                ExtraResponseHeadersMiddleware,
                headers={'Cache-Control': 'no-store'})
        if allowed_origins:
            app.add_middleware(
                CORSMiddleware, allow_origins=allowed_origins,
                allow_credentials=True, allow_methods=['*'],
                allow_headers=['*'])
        L.info('serving at http://%s:%s%s', host, port, root_uri)
        try:
            uvicorn.run(
                app, host=host, port=port,
                access_log=L.getEffectiveLevel() <= DEBUG)
        except AssertionError:
            L.error(f'could not start server at {host}:{port}')

    def watch(
            self, configuration, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds, reload):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('watchgod.watcher').setLevel(ERROR)
        server_process, disk_database = self._start(configuration)
        for changed_packs in watch(
                configuration.folder, min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            L.debug(changed_packs)
            changed_paths = [_[1] for _ in changed_packs]
            changed_infos = disk_database.grok(changed_paths)
            L.debug(changed_infos)
            should_restart_server = False
            for info in changed_infos:
                if info['code'] == 'c':
                    should_restart_server = True
            if self._with_restart and should_restart_server:
                try:
                    configuration = reload()
                except CrossComputeError as e:
                    L.error(e)
                    continue
                server_process.stop()
                server_process, disk_database = self._start(configuration)

    def _start(self, configuration):
        server_process = StoppableProcess(
            name='server', target=self.serve, args=(configuration,))
        server_process.start()
        disk_database = DiskDatabase(configuration, self._changes)
        return server_process, disk_database

    def _refresh(self, configuration):
        configuration_name = configuration.name
        if configuration_name == 'Automation 0':
            configuration_name = 'Automations'
        configuration_folder = configuration.folder
        root_uri, with_restart = self._root_uri, self._with_restart
        site.update({
            'name': configuration_name, 'configuration': configuration,
            'definitions': configuration.automation_definitions,
            'environment': self._environment, 'safe': self._safe,
            'queue': self._queue, 'changes': self._changes})
        template_path_by_id.update(TEMPLATE_PATH_BY_ID)
        for template_id, path in configuration.template_path_by_id.items():
            template_path_by_id[template_id] = str(configuration_folder / path)
        template_globals.update({
            'base_template_path': template_path_by_id['base'],
            'live_template_path': template_path_by_id['live'],
            'server_timestamp': time(), 'root_uri': root_uri,
            'with_restart': with_restart})
        template_environment.auto_reload = with_restart


def get_app(root_uri):
    app = FastAPI(root_path=root_uri)
    app.include_router(root.router)
    app.include_router(automation.router)
    app.include_router(mutation.router)
    app.include_router(token.router)
    return app


L = getLogger(__name__)
getLogger('uvicorn.error').propagate = False

from logging import getLogger, DEBUG
from os import getenv
from time import time

import uvicorn
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from invisibleroads_macros_web.starlette import ExtraResponseHeadersMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from watchfiles import watch

from ..constants import HOST, PORT, TEMPLATE_PATH_BY_ID
from ..exceptions import CrossComputeError
from ..routers import automation, mutation, root, token
from ..settings import (
    StoppableProcess, site, template_environment, template_globals,
    template_path_by_id)
from .database import DiskDatabase
from .interface import Server


class DiskServer(Server):

    def __init__(
            self, environment, safe, queue, work, changes,
            host=HOST, port=PORT, with_restart=True, with_prefix=True,
            with_hidden=True, root_uri='', allowed_origins=None):
        self._environment = environment
        self._safe = safe
        self._queue = queue
        self._work = work
        self._changes = changes
        self._host = host
        self._port = port
        self._with_restart = with_restart
        self._with_prefix = with_prefix
        self._with_hidden = with_hidden
        self._root_uri = root_uri
        self._allowed_origins = allowed_origins

    def serve(self, configuration):
        worker_process = StoppableProcess(
            name='worker', target=self._work, args=(self._queue,))
        worker_process.start()
        host, port, root_uri, with_restart, with_prefix, allowed_origins = [
            self._host, self._port, self._root_uri, self._with_restart,
            self._with_prefix, self._allowed_origins]
        self._refresh(configuration)
        app = get_app(root_uri, with_prefix)
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
        except KeyboardInterrupt:
            pass
        except Exception as e:
            L.exception(e)
        finally:
            worker_process.stop()

    def watch(
            self, configuration, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds, reload):
        server_process, disk_database = self._start(configuration)
        try:
            for changed_packs in watch(
                    configuration.folder, step=disk_poll_in_milliseconds,
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
        except KeyboardInterrupt:
            pass
        except Exception as e:
            L.exception(e)
        finally:
            server_process.stop()

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
            'name': configuration_name,
            'configuration': configuration,
            'definitions': configuration.automation_definitions,
            'environment': self._environment,
            'safe': self._safe,
            'queue': self._queue,
            'changes': self._changes,
            'with_prefix': self._with_prefix,
            'with_hidden': self._with_hidden})
        template_path_by_id.update(TEMPLATE_PATH_BY_ID)
        for template_id, path in configuration.template_path_by_id.items():
            template_path_by_id[template_id] = str(configuration_folder / path)
        template_globals.update({
            'base_template_path': template_path_by_id['base'],
            'live_template_path': template_path_by_id['live'],
            'google_analytics_id': getenv('GOOGLE_ANALYTICS_ID', ''),
            'server_timestamp': time(),
            'root_uri': root_uri,
            'with_restart': with_restart})
        template_environment.auto_reload = with_restart


def get_app(root_uri, with_prefix):
    prefix = root_uri if with_prefix else ''
    app = FastAPI(root_path='' if with_prefix else root_uri)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.include_router(root.router, prefix=prefix)
    app.include_router(automation.router, prefix=prefix)
    app.include_router(mutation.router, prefix=prefix)
    app.include_router(token.router, prefix=prefix)
    return app


async def handle_http_exception(request, e):
    if request.url.path.endswith('.json'):
        response = await http_exception_handler(request, e)
    else:
        response = PlainTextResponse(status_code=e.status_code)
    return response


L = getLogger(__name__)
getLogger('uvicorn.error').propagate = False

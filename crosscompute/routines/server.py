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

from ..constants import (
    Info,
    BUTTON_TEXT_BY_ID,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_STEP_IN_MILLISECONDS,
    HOST,
    PORT,
    TEMPLATE_PATH_BY_ID)
from ..exceptions import (
    CrossComputeError)
from ..routers import (
    automation,
    file,
    root,
    stream,
    token)
from ..settings import (
    StoppableProcess,
    button_text_by_id,
    site,
    template_environment,
    template_globals,
    template_path_by_id)
from .database import (
    DiskDatabase,
    PositiveFileFilter)
from .interface import (
    Server)


class DiskServer(Server):

    def __init__(
            self, work, environment, safe,
            uris, tasks, changes,
            host=HOST, port=PORT, root_uri='', allowed_origins=None,
            with_restart=True, with_prefix=True, with_hidden=True):
        self._work = work
        self._environment = environment
        self._safe = safe
        self._uris = uris
        self._tasks = tasks
        self._changes = changes
        self._host = host
        self._port = port
        self._root_uri = root_uri
        self._allowed_origins = allowed_origins
        self._with_restart = with_restart
        self._with_prefix = with_prefix
        self._with_hidden = with_hidden

    def serve(self, configuration):
        host, port, root_uri, allowed_origins = [
            self._host, self._port, self._root_uri, self._allowed_origins]
        app = get_app(root_uri, self._with_prefix)
        if self._with_restart:
            app.add_middleware(ExtraResponseHeadersMiddleware, headers={
                'Cache-Control': 'no-store'})
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

    def watch(self, configuration, reload):
        s_process, w_process, d_database = self.start(configuration)
        try:
            for changed_packs in watch(
                    configuration.folder,
                    watch_filter=PositiveFileFilter(),
                    debounce=DISK_DEBOUNCE_IN_MILLISECONDS,
                    step=DISK_STEP_IN_MILLISECONDS):
                changed_paths = [_[1] for _ in changed_packs]
                changed_infos = d_database.grok(changed_paths)
                should_restart_server = False
                for info in changed_infos:
                    if info['code'] == Info.CONFIGURATION:
                        should_restart_server = True
                if self._with_restart and should_restart_server:
                    try:
                        configuration = reload()
                    except CrossComputeError as e:
                        L.error(e)
                        continue
                    s_process.stop()
                    w_process.stop()
                    s_process, w_process, d_database = self.start(
                        configuration)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            L.exception(e)
        finally:
            s_process.stop()
            w_process.stop()

    def start(self, configuration):
        self.refresh(configuration)
        server_process = StoppableProcess(
            name='server', target=self.serve,
            args=(configuration,))
        server_process.start()
        worker_process = StoppableProcess(
            name='worker', target=self._work,
            args=(
                configuration.automation_definitions,
                self._tasks,
                self._uris,
                self._changes,
                self._environment,
                f'http://127.0.0.1:{self._port}{self._root_uri}'),
            kwargs={'with_rebuild': True})
        worker_process.start()
        disk_database = DiskDatabase(
            configuration, self._changes, self._with_restart)
        return server_process, worker_process, disk_database

    def refresh(self, configuration):
        name = configuration.name
        site.update({
            'name': 'Automations' if name == 'Automation 0' else name,
            'configuration': configuration,
            'definitions': configuration.automation_definitions,
            'environment': self._environment,
            'safe': self._safe,
            'uris': self._uris,
            'tasks': self._tasks,
            'changes': self._changes,
            'with_prefix': self._with_prefix,
            'with_hidden': self._with_hidden})
        template_path_by_id.update(TEMPLATE_PATH_BY_ID)
        for template_id, path in configuration.template_path_by_id.items():
            template_path_by_id[template_id] = str(configuration.folder / path)
        template_globals.update({
            'base_template_path': template_path_by_id['base'],
            'live_template_path': template_path_by_id['live'],
            'google_analytics_id': getenv('GOOGLE_ANALYTICS_ID', ''),
            'server_time': time(),
            'root_uri': self._root_uri,
            'with_restart': self._with_restart})
        template_environment.auto_reload = self._with_restart
        button_text_by_id.update(BUTTON_TEXT_BY_ID)
        button_text_by_id.update(configuration.button_text_by_id)


def get_app(root_uri, with_prefix):
    prefix = root_uri if with_prefix else ''
    app = FastAPI(root_path='' if with_prefix else root_uri)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.include_router(root.router, prefix=prefix)
    app.include_router(automation.router, prefix=prefix)
    app.include_router(file.router, prefix=prefix)
    app.include_router(token.router, prefix=prefix)
    app.include_router(stream.router, prefix=prefix)
    return app


async def handle_http_exception(request, e):
    if request.url.path.endswith('.json'):
        response = await http_exception_handler(request, e)
    else:
        response = PlainTextResponse(status_code=e.status_code)
    return response


L = getLogger(__name__)
getLogger('uvicorn.error').propagate = False

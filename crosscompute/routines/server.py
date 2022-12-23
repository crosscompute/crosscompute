from logging import getLogger, DEBUG, ERROR
from time import time

import uvicorn
from fastapi import FastAPI
from invisibleroads_macros_process import LoggableProcess, StoppableProcess
from watchgod import watch

from ..constants import HOST, PORT
from ..exceptions import CrossComputeError
from ..routers import automation, mutation, root, token
from ..variables import site, template_environment
from .database import DiskDatabase
from .interface import Server


class DiskServer(Server):

    def __init__(
            self, environment, safe, queue, work, changes,
            host=HOST, port=PORT, with_refresh=False,
            with_restart=False, root_uri='', allowed_origins=None):
        self._environment = environment
        self._safe = safe
        self._queue = queue
        self._work = work
        self._changes = changes
        self._host = host
        self._port = port
        self._with_refresh = with_refresh
        self._with_restart = with_restart
        self._root_uri = root_uri
        self._allowed_origins = allowed_origins

    def serve(self, configuration):
        worker_process = LoggableProcess(
            name='worker', target=self._work, args=(self._queue,))
        worker_process.start()
        host, port, root_uri = self._host, self._port, self._root_uri
        site.update({
            'name': configuration.name,
            'configuration': configuration,
            'definitions': configuration.automation_definitions,
            'queue': self._queue,
            'environment': self._environment,
            'changes': self._changes})
        template_environment.globals.update({
            'server_timestamp': time(),
        })
        # self._safe, self._with_refresh, with_restart, self._allowed_origins
        app = get_app(root_uri)
        L.info('serving at http://%s:%s%s', host, port, root_uri)
        try:
            uvicorn.run(
                app,
                host=host,
                port=port,
                access_log=L.getEffectiveLevel() <= DEBUG)
        except AssertionError:
            L.error(f'could not start server at {host}:{port}')

    def watch(
            self, configuration, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds, reload):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('watchgod.watcher').setLevel(ERROR)
        server_process, disk_database = self._serve(configuration)
        automation_folder = configuration.folder
        for changed_packs in watch(
                automation_folder, min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            L.debug(changed_packs)
            changed_paths = [_[1] for _ in changed_packs]
            changed_infos = disk_database.grok(changed_paths)
            L.debug(changed_infos)
            should_restart_server = False
            for info in changed_infos:
                if info['code'] == 'c':
                    should_restart_server = True
            if should_restart_server:
                try:
                    configuration = reload()
                except CrossComputeError as e:
                    L.error(e)
                    continue
                server_process.stop()
                server_process, disk_database = self._serve(configuration)

    def _serve(self, configuration):
        server_process = StoppableProcess(
            name='server', target=self.serve, args=(configuration,))
        server_process.start()
        disk_database = DiskDatabase(configuration, self._changes)
        return server_process, disk_database


def get_app(root_uri):
    app = FastAPI(root_path=root_uri)
    app.include_router(root.router)
    app.include_router(automation.router)
    app.include_router(mutation.router)
    app.include_router(token.router)
    return app


'''
def _get_app(
        configuration, environment, safe, queue, with_refresh, with_restart,
        root_uri, allowed_origins, changes):
    server_timestamp = time()
    settings = {
        'root_uri': root_uri,
        'jinja2.trim_blocks': True,
        'jinja2.lstrip_blocks': True,
    }
    if with_refresh and with_restart:
        settings.update({'pyramid.reload_templates': True})
    with Configurator(settings=settings) as config:
        config.include('pyramid_jinja2')
        config.add_jinja2_renderer('.html')
        _configure_automation_routes(
            config, configuration, safe, environment, queue)
        if with_refresh:
            _configure_mutation_routes(
                config, server_timestamp, changes)
        _configure_token_routes(
            config, configuration, safe)
        _configure_renderer_globals(
            config, with_refresh, with_restart, root_uri, server_timestamp,
            configuration)
        _configure_cache_headers(config, with_restart)
        _configure_allowed_origins(config, allowed_origins)
    safe.constant_value_by_key = configuration.identities_by_token
    return config.make_wsgi_app()


def _configure_token_routes(
        config, configuration, safe):
    token_routes = TokenRoutes(
        configuration, safe)
    config.include(token_routes.includeme)


def _configure_automation_routes(
        config, configuration, safe, environment, queue):
    automation_routes = AutomationRoutes(
        configuration, safe, environment, queue)
    config.include(automation_routes.includeme)


def _configure_mutation_routes(config, server_timestamp, changes):
    mutation_routes = MutationRoutes(server_timestamp, changes)
    config.include(mutation_routes.includeme)


def _configure_renderer_globals(
        config, with_refresh, with_restart, root_uri, server_timestamp,
        configuration):
    if configuration.template_path_by_id:
        config.add_jinja2_search_path(str(
            configuration.folder), prepend=True, name='.html')

    def update_renderer_globals():
        config.get_jinja2_environment(name='.html').globals.update({
            'SERVER_TIMESTAMP': server_timestamp,
        })

    config.action(None, update_renderer_globals)


def _configure_cache_headers(config, with_restart):
    if not with_restart:
        return

    def update_cache_headers(e):
        e.response.headers.update({'Cache-Control': 'no-store'})

    config.add_subscriber(update_cache_headers, NewResponse)


def _configure_allowed_origins(config, allowed_origins):
    if not allowed_origins:
        return

    def update_cors_headers(e):
        request_headers = e.request.headers
        if 'Origin' not in request_headers:
            return
        origin = request_headers['Origin']
        if origin not in allowed_origins:
            return
        e.response.headers.update({
            'Access-Control-Allow-Origin': origin})

    config.add_subscriber(update_cors_headers, NewResponse)
'''


L = getLogger(__name__)
getLogger('uvicorn.error').propagate = False

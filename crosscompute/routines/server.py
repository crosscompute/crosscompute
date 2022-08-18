from logging import getLogger, DEBUG, ERROR
from time import time

from pyramid.config import Configurator
from pyramid.events import NewResponse
from waitress import serve
from watchgod import watch

from ..constants import (
    HOST,
    MAXIMUM_PING_INTERVAL_IN_SECONDS,
    MINIMUM_PING_INTERVAL_IN_SECONDS,
    PORT)
from ..exceptions import (
    CrossComputeError)
from ..macros.process import LoggableProcess, StoppableProcess
from ..routes.authorization import AuthorizationRoutes
from ..routes.automation import AutomationRoutes
from ..routes.mutation import MutationRoutes
from .database import DiskDatabase
from .interface import Server


class DiskServer(Server):

    def __init__(
            self, environment, safe, queue, work, infos_by_timestamp,
            host=HOST, port=PORT, with_refresh=False,
            with_restart=False, root_uri='', allowed_origins=None):
        self._environment = environment
        self._safe = safe
        self._queue = queue
        self._work = work
        self._infos_by_timestamp = infos_by_timestamp
        self._host = host
        self._port = port
        self._with_refresh = with_refresh
        self._with_restart = with_restart
        self._root_uri = root_uri
        self._allowed_origins = allowed_origins

    def serve(self, configuration):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('waitress').setLevel(ERROR)
        worker_process = LoggableProcess(
            name='worker', target=self._work, args=(self._queue,))
        worker_process.daemon = True
        worker_process.start()
        # TODO: Decouple from pyramid and waitress
        host, port, root_uri = self._host, self._port, self._root_uri
        app = _get_app(
            configuration, self._environment, self._safe, self._queue,
            self._with_refresh, self._with_restart, root_uri,
            self._allowed_origins, self._infos_by_timestamp)
        L.info('serving at http://%s:%s%s', host, port, root_uri)
        try:
            serve(app, host=host, port=port, url_prefix=root_uri)
        except OSError as e:
            L.error(e)

    def watch(
            self, configuration, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds, reload):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('watchgod.watcher').setLevel(ERROR)
        server_process, disk_database = self._serve(configuration)
        automation_folder = configuration.folder
        for changes in watch(
                automation_folder, min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            L.debug(changes)
            changed_paths = [_[1] for _ in changes]
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
        disk_database = DiskDatabase(configuration, self._infos_by_timestamp)
        return server_process, disk_database


def _get_app(
        configuration, environment, safe, queue, with_refresh, with_restart,
        root_uri, allowed_origins, infos_by_timestamp):
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
        _configure_authorization_routes(
            config, configuration, safe)
        _configure_automation_routes(
            config, configuration, safe, environment, queue)
        if with_refresh:
            _configure_mutation_routes(
                config, server_timestamp, infos_by_timestamp)
        _configure_renderer_globals(
            config, with_refresh, with_restart, root_uri, server_timestamp,
            configuration)
        _configure_cache_headers(config, with_restart)
        _configure_allowed_origins(config, allowed_origins)
    safe.constant_value_by_key = configuration.identities_by_token
    return config.make_wsgi_app()


def _configure_authorization_routes(
        config, configuration, safe):
    authorization_routes = AuthorizationRoutes(
        configuration, safe)
    config.include(authorization_routes.includeme)


def _configure_automation_routes(
        config, configuration, safe, environment, queue):
    automation_routes = AutomationRoutes(
        configuration, safe, environment, queue)
    config.include(automation_routes.includeme)


def _configure_mutation_routes(config, server_timestamp, infos_by_timestamp):
    mutation_routes = MutationRoutes(server_timestamp, infos_by_timestamp)
    config.include(mutation_routes.includeme)


def _configure_renderer_globals(
        config, with_refresh, with_restart, root_uri, server_timestamp,
        configuration):
    if configuration.template_path_by_id:
        config.add_jinja2_search_path(str(configuration.folder), prepend=True)

    def update_renderer_globals():
        config.get_jinja2_environment().globals.update({
            'BASE_JINJA2': configuration.get_template_path('base'),
            'LIVE_JINJA2': configuration.get_template_path('live'),
            'WITH_REFRESH': with_refresh,
            'ROOT_URI': root_uri,
            'MAXIMUM_PING_INTERVAL': MAXIMUM_PING_INTERVAL_IN_SECONDS * 1000,
            'MINIMUM_PING_INTERVAL': MINIMUM_PING_INTERVAL_IN_SECONDS * 1000,
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


L = getLogger(__name__)

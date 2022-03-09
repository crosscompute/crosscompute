from invisibleroads_macros_disk import is_path_in_folder
from logging import getLogger, DEBUG, ERROR
from multiprocessing import Queue
from pathlib import Path
from pyramid.config import Configurator
from pyramid.events import NewResponse
from time import time
from waitress import serve
from watchgod import watch

from ..constants import (
    HOST,
    MAXIMUM_PING_INTERVAL_IN_SECONDS,
    MINIMUM_PING_INTERVAL_IN_SECONDS,
    MODE_CODE_BY_NAME,
    MODE_ROUTE,
    PORT,
    RUN_ROUTE)
from ..exceptions import (
    CrossComputeError)
from ..macros.process import LoggableProcess, StoppableProcess
from ..routes.automation import AutomationRoutes
from ..routes.mutation import MutationRoutes
from .interface import Server


class DiskServer(Server):

    def __init__(self, work, queue=None, settings=None):
        if not queue:
            queue = Queue()
        if not settings:
            settings = {}
        self._work = work
        self._queue = queue
        self._host = settings.get('host', HOST)
        self._port = settings.get('port', PORT)
        self._is_static = settings.get('is_static', False)
        self._is_production = settings.get('is_production', False)
        self._base_uri = settings.get('base_uri', '')
        self._allowed_origins = settings.get('allowed_origins')
        self._infos_by_timestamp = settings.get('infos_by_timestamp', {})

    def run(self, configuration):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('waitress').setLevel(ERROR)
        worker_process = LoggableProcess(
            name='worker', target=self._work, args=(self._queue,))
        worker_process.daemon = True
        worker_process.start()
        # TODO: Decouple from pyramid and waitress
        host = self._host
        port = self._port
        base_uri = self._base_uri
        app = _get_app(
            configuration,
            self._queue,
            self._is_static,
            self._is_production,
            base_uri,
            self._allowed_origins,
            self._infos_by_timestamp)
        L.info('serving at http://%s:%s%s', host, port, base_uri)
        try:
            serve(
                app,
                host=host,
                port=port,
                url_prefix=base_uri)
        except OSError as e:
            L.error(e)

    def watch(
            self,
            configuration,
            disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds,
            reload):
        if L.getEffectiveLevel() > DEBUG:
            getLogger('watchgod.watcher').setLevel(ERROR)
        server_process, info_by_path = self._run(configuration)
        automation_folder = configuration.folder
        for changes in watch(
                automation_folder,
                min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            should_restart_server = False
            changed_infos = []
            for changed_type, changed_path in changes:
                try:
                    changed_info = _get_info(
                        configuration, changed_path, info_by_path)
                except KeyError:
                    continue
                if changed_info['code'] == 'c':
                    should_restart_server = True
                changed_infos.append(changed_info)
                L.debug('%s %s %s', changed_type, changed_path, changed_info)
            if should_restart_server:
                try:
                    configuration = reload()
                except CrossComputeError as e:
                    L.error(e)
                    continue
                server_process.stop()
                server_process, info_by_path = self._run(configuration)
            if changed_infos:
                self._infos_by_timestamp[time()] = changed_infos

    def _run(self, configuration):
        server_process = StoppableProcess(
            name='server', target=self.run, args=(configuration,))
        server_process.start()
        info_by_path = _get_info_by_path(configuration)
        return server_process, info_by_path


def _get_app(
        configuration,
        queue,
        is_static,
        is_production,
        base_uri,
        allowed_origins,
        infos_by_timestamp):
    server_timestamp = time()
    automation_definitions = configuration.automation_definitions
    automation_routes = AutomationRoutes(
        configuration, automation_definitions, queue)
    settings = {
        'base_uri': base_uri,
        'jinja2.trim_blocks': True,
        'jinja2.lstrip_blocks': True,
    }
    if not is_static and not is_production:
        settings.update({'pyramid.reload_templates': True})
    with Configurator(settings=settings) as config:
        config.include('pyramid_jinja2')
        config.include(automation_routes.includeme)
        if not is_static:
            mutation_routes = MutationRoutes(
                server_timestamp, infos_by_timestamp)
            config.include(mutation_routes.includeme)
        _configure_renderer_globals(
            config, is_static, is_production, base_uri, server_timestamp,
            configuration)
        _configure_cache_headers(config, is_production)
        _configure_allowed_origins(config, allowed_origins)
    return config.make_wsgi_app()


def _configure_renderer_globals(
        config, is_static, is_production, base_uri, server_timestamp,
        configuration):
    if configuration.template_path_by_id:
        config.add_jinja2_search_path(str(configuration.folder), prepend=True)

    def update_renderer_globals():
        config.get_jinja2_environment().globals.update({
            'BASE_JINJA2': configuration.get_template_path('base'),
            'LIVE_JINJA2': configuration.get_template_path('live'),
            'IS_STATIC': is_static,
            'IS_PRODUCTION': is_production,
            'BASE_URI': base_uri,
            'MAXIMUM_PING_INTERVAL': MAXIMUM_PING_INTERVAL_IN_SECONDS * 1000,
            'MINIMUM_PING_INTERVAL': MINIMUM_PING_INTERVAL_IN_SECONDS * 1000,
            'SERVER_TIMESTAMP': server_timestamp,
        })

    config.action(None, update_renderer_globals)


def _configure_cache_headers(config, is_production):
    if is_production:
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


def _get_info(configuration, path, info_by_path):
    path = Path(path)
    real_path = path.resolve()
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        runs_folder = automation_folder / 'runs'
        if not is_path_in_folder(path, runs_folder):
            continue
        run_id = path.absolute().relative_to(runs_folder).parts[0]
        run_uri = RUN_ROUTE.format(run_slug=run_id)
        variable_packs = _get_variable_packs_from_folder(
            configuration, runs_folder / run_id, run_uri)
        for path, info in variable_packs:
            if real_path == path.resolve():
                return info
    return info_by_path[real_path]


def _get_info_by_path(configuration):
    'Set c = configuration, v = variable, t = template, s = style'
    packs = []
    packs.extend(_get_configuration_packs(configuration))
    packs.extend(_get_variable_packs(configuration))
    packs.extend(_get_template_packs(configuration))
    packs.extend(_get_style_packs(configuration))
    return {path.resolve(): info for path, info in packs}


def _get_configuration_packs(configuration):
    packs = []
    automation_definitions = configuration.automation_definitions
    # Get automation configuration paths
    packs.append((configuration.path, {}))
    for automation_definition in automation_definitions:
        packs.append((automation_definition.path, {}))
    # Get batch configuration paths
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        # Use raw batch definitions
        raw_batch_definitions = automation_definition.get('batches', [])
        for raw_batch_definition in raw_batch_definitions:
            batch_configuration = raw_batch_definition.get(
                'configuration', {})
            if 'path' not in batch_configuration:
                continue
            path = automation_folder / batch_configuration['path']
            packs.append((path, {}))
    for path, d in packs:
        d['code'] = 'c'
    return packs


def _get_variable_packs(configuration):
    packs = []
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        # Use computed batch definitions
        for batch_definition in automation_definition.batch_definitions:
            batch_uri = batch_definition.uri
            variable_packs = _get_variable_packs_from_folder(
                configuration,
                automation_folder / batch_definition.folder,
                batch_uri)
            packs.extend(variable_packs)
    return packs


def _get_variable_packs_from_folder(
        configuration, absolute_batch_folder, batch_uri):
    packs = []
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_uri = automation_definition.uri
        d = automation_definition.variable_definitions_by_mode_name
        for mode_name, variable_definitions in d.items():
            mode_code = MODE_CODE_BY_NAME[mode_name]
            mode_uri = MODE_ROUTE.format(mode_code=mode_code)
            folder = absolute_batch_folder / mode_name
            for variable_definition in variable_definitions:
                variable_id = variable_definition.id
                info = {
                    'id': variable_id,
                    'uri': automation_uri + batch_uri + mode_uri}
                variable_configuration = variable_definition.configuration
                if 'path' in variable_configuration:
                    path = folder / variable_configuration['path']
                    packs.append((path, info))
                path = folder / variable_definition.path
                packs.append((path, info))
    for path, d in packs:
        d['code'] = 'v'
    return packs


def _get_template_packs(configuration):
    packs = []
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        automation_uri = automation_definition.uri
        d = automation_definition.template_definitions_by_mode_name
        for mode_name, template_definitions in d.items():
            for template_definition in template_definitions:
                if 'path' not in template_definition:
                    continue
                path = automation_folder / template_definition.path
                packs.append((path, {
                    'mode_name': mode_name, 'uri': automation_uri}))
        d = automation_definition.template_path_by_id
        for template_id, path in d.items():
            packs.append((automation_folder / path, {
                'id': template_id, 'uri': automation_uri}))
    for path, d in packs:
        d['code'] = 't'
    return packs


def _get_style_packs(configuration):
    packs = []
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        for style_definition in automation_definition.style_definitions:
            if 'path' not in style_definition:
                continue
            path = automation_folder / style_definition['path']
            packs.append((path, {}))
    for path, d in packs:
        d['code'] = 's'
    return packs


L = getLogger(__name__)

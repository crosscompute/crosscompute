import multiprocessing as mp

from invisibleroads_macros_web.jinja import (
    PathTemplateLoader,
    RelativeTemplateEnvironment)
from invisibleroads_macros_web.starlette import (
    TemplateResponseFactory)

from .constants import (
    ASSETS_FOLDER,
    MAXIMUM_PING_INTERVAL_IN_SECONDS,
    MINIMUM_PING_INTERVAL_IN_SECONDS)


multiprocessing_context = mp.get_context('fork')
site = {
    'name': 'Automations',
    'configuration': None,
    'definitions': [],
    'environment': {},
    'safe': None,
    'queue': None,
    'changes': {}}
template_path_by_id = {
    'base': str(ASSETS_FOLDER / 'base.html'),
    'live': str(ASSETS_FOLDER / 'live.html'),
    'root': str(ASSETS_FOLDER / 'root.html'),
    'automation': str(ASSETS_FOLDER / 'automation.html'),
    'batch': str(ASSETS_FOLDER / 'batch.html'),
    'step': str(ASSETS_FOLDER / 'step.html')}
template_environment = RelativeTemplateEnvironment(
    loader=PathTemplateLoader(),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True)
template_globals = template_environment.globals = {
    'base_template_path': template_path_by_id['base'],
    'live_template_path': template_path_by_id['live'],
    'maximum_ping_interval_in_milliseconds':
        MAXIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'minimum_ping_interval_in_milliseconds':
        MINIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'server_timestamp': 0,
    'root_uri': '',
    'with_restart': True}
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

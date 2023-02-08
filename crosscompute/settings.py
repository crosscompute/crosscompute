import multiprocessing as mp
from os import getenv

from invisibleroads_macros_web.jinja import (
    PathTemplateLoader,
    RelativeTemplateEnvironment)
from invisibleroads_macros_web.starlette import (
    TemplateResponseFactory)

from .constants import (
    MAXIMUM_PING_INTERVAL_IN_SECONDS,
    MINIMUM_PING_INTERVAL_IN_SECONDS,
    TEMPLATE_PATH_BY_ID)


multiprocessing_context = mp.get_context('fork')
site = {
    'name': 'Automations',
    'configuration': None,
    'definitions': [],
    'environment': {},
    'safe': None,
    'queue': None,
    'changes': {},
    'with_prefix': False}
template_path_by_id = TEMPLATE_PATH_BY_ID.copy()
template_environment = RelativeTemplateEnvironment(
    loader=PathTemplateLoader(),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True)
template_globals = template_environment.globals = {
    'base_template_path': template_path_by_id['base'],
    'live_template_path': template_path_by_id['live'],
    'google_analytics_id': getenv('GOOGLE_ANALYTICS_ID', ''),
    'maximum_ping_interval_in_milliseconds':
        MAXIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'minimum_ping_interval_in_milliseconds':
        MINIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'server_timestamp': 0,
    'root_uri': '',
    'with_restart': True}
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

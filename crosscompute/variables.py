# TODO: Set template_environment.auto_reload dynamically
from invisibleroads_macros_web.fastapi import (
    TemplateResponseFactory)
from invisibleroads_macros_web.jinja import (
    PathTemplateLoader,
    RelativeTemplateEnvironment,
    url_for)

from .constants import (
    MAXIMUM_PING_INTERVAL_IN_SECONDS,
    MINIMUM_PING_INTERVAL_IN_SECONDS,
    TEMPLATES_FOLDER)


site_settings = {
    'name': 'Automations',
}
user_variables = {}
automation_definitions = []
template_path_by_id = {
    'base': str(TEMPLATES_FOLDER / 'base.html'),
    'live': str(TEMPLATES_FOLDER / 'live.html'),
    'root': str(TEMPLATES_FOLDER / 'root.html'),
    'automation': str(TEMPLATES_FOLDER / 'automation.html'),
    'batch': str(TEMPLATES_FOLDER / 'batch.html'),
    'step': str(TEMPLATES_FOLDER / 'step.html'),
}
template_environment = RelativeTemplateEnvironment(
    loader=PathTemplateLoader(),
    autoescape=True,
    trim_blocks=True)
template_environment.globals = {
    'with_refresh': True,
    'base_template_path': template_path_by_id['base'],
    'live_template_path': template_path_by_id['live'],
    'maximum_ping_interval_in_milliseconds':
        MAXIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'minimum_ping_interval_in_milliseconds':
        MINIMUM_PING_INTERVAL_IN_SECONDS * 1000,
    'server_timestamp': 0,
    'root_uri': '',
    'url_for': url_for,
}
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

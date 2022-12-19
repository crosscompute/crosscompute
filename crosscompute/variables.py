# TODO: Set template_environment.auto_reload dynamically
from invisibleroads_macros_web.fastapi import (
    TemplateResponseFactory)
from invisibleroads_macros_web.jinja import (
    PathTemplateLoader,
    RelativeTemplateEnvironment,
    url_for)

from .constants import (
    TEMPLATES_FOLDER)


site_settings = {
    'name': 'Automations',
}
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
    'root_uri': '',
    'url_for': url_for,
}
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse
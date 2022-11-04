# TODO: Set template_environment.auto_reload dynamically
from invisibleroads_macros_web.fastapi import (
    TemplateResponseFactory)
from invisibleroads_macros_web.jinja import (
    PathTemplateLoader,
    RelativeTemplateEnvironment,
    url_for)

from .constants import (
    TEMPLATES_FOLDER)


template_path_by_id = {
    'base': str(TEMPLATES_FOLDER / 'base.html'),
    'live': str(TEMPLATES_FOLDER / 'live.html'),
    'root': str(TEMPLATES_FOLDER / 'root.html'),
}
template_environment = RelativeTemplateEnvironment(
    loader=PathTemplateLoader(),
    autoescape=True,
    trim_blocks=True)
template_environment.globals = {
    'BASE_PATH': template_path_by_id['base'],
    'LIVE_PATH': template_path_by_id['live'],
    'url_for': url_for,
}
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

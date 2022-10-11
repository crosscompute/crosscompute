# TODO: Set template_environment.auto_reload dynamically
from invisibleroads_macros_web.fastapi import (
    TemplateResponseFactory)
from invisibleroads_macros_web.jinja import (
    RelativeTemplateEnvironment,
    TemplatePathLoader,
    url_for)


template_environment = RelativeTemplateEnvironment(
    loader=TemplatePathLoader(),
    autoescape=True,
    trim_blocks=True,
    globals={'url_for': url_for})
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

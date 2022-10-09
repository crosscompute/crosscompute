# TODO: Set templates.env.auto_reload dynamically

from .routines.template import (
    RelativeTemplateEnvironment,
    TemplatePathLoader,
    TemplateResponseFactory,
    url_for)


template_environment = RelativeTemplateEnvironment(
    loader=TemplatePathLoader(),
    autoescape=True,
    trim_blocks=True,
    globals={'url_for': url_for})
TemplateResponse = TemplateResponseFactory(
    template_environment).TemplateResponse

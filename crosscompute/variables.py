from fastapi.templating import Jinja2Templates

from .constants import (
    TEMPLATES_FOLDER)


default_templates = Jinja2Templates(
    directory=TEMPLATES_FOLDER,
    trim_blocks=True)
# TODO: Set templates.env.auto_reload dynamically
DefaultTemplateResponse = default_templates.TemplateResponse


# custom_templates = Jinja2Templates()

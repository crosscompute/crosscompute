# TODO: Set templates.env.auto_reload dynamically
from fastapi.templating import Jinja2Templates

from .constants import (
    TEMPLATES_FOLDER)
from .routines.configuration import (
    PathLoader)


TemplateResponse = Jinja2Templates(
    directory=TEMPLATES_FOLDER,
    trim_blocks=True,
).TemplateResponse

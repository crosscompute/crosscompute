from os.path import join
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    STYLE_ROUTE)


class AutomationViews():

    def __init__(self, configuration, configuration_folder):
        display_configuration = configuration.get('display', {})
        style_configuration = display_configuration.get('style', {})
        style_path = join(
            configuration_folder, style_configuration.get('path'))

        self.configuration = configuration
        self.configuration_folder = configuration_folder
        self.style_path = style_path
        self.style_urls = [STYLE_ROUTE] if style_path else []

    def includeme(self, config):
        config.include(self.configure_stylesheets)

        config.add_route('home', '/')

        config.add_view(
            self.see_home,
            route_name='home',
            renderer='crosscompute:templates/home.jinja2')

    def configure_stylesheets(self, config):
        if not self.style_path:
            return

        config.add_route('style', STYLE_ROUTE)
        config.add_view(
            self.see_style,
            route_name='style')

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'style': {'urls': self.style_urls},
            })

        config.action(None, update_renderer_globals)

    def see_home(self, request):
        return {}

    def see_style(self, request):
        style_path = self.style_path
        if not style_path:
            raise HTTPNotFound
        return FileResponse(style_path, request)

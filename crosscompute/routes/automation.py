from os.path import join
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    STYLE_ROUTE)
from ..macros.iterable import find_item
from ..routines.configuration import (
    get_css_uris)


class AutomationRoutes():

    def __init__(
            self, automation_definitions, automation_queue, timestamp_object):
        self.automation_definitions = automation_definitions
        self.automation_queue = automation_queue
        self.timestamp_object = timestamp_object

    def includeme(self, config):
        config.include(self.configure_root)
        config.include(self.configure_styles)

    def configure_styles(self, config):
        config.add_route(
            'style', STYLE_ROUTE)
        config.add_route(
            'automation style', AUTOMATION_ROUTE + STYLE_ROUTE)

        config.add_view(
            self.see_style,
            route_name='style')
        config.add_view(
            self.see_style,
            route_name='automation style')

    def configure_root(self, config):
        config.add_route('root', '/')

        config.add_view(
            self.see_root,
            route_name='root',
            renderer='crosscompute:templates/root.jinja2')

    def see_root(self, request):
        'Render root with a list of available automations'
        automation_definitions = self.automation_definitions
        for automation_definition in automation_definitions:
            if 'parent' not in automation_definition:
                css_uris = get_css_uris(automation_definition)
                break
        else:
            css_uris = []
        return {
            'automations': automation_definitions,
            'css_uris': css_uris,
            'timestamp_value': self.timestamp_object.value,
        }

    def see_style(self, request):
        matchdict = request.matchdict
        automation_definitions = self.automation_definitions
        if 'automation_slug' in matchdict:
            automation_definition = self.get_automation_definition_from(
                request)
        elif automation_definitions:
            automation_definition = automation_definitions[0]
            if 'parent' in automation_definition:
                automation_definition = automation_definition['parent']
        else:
            raise HTTPNotFound
        style_definitions = automation_definition.get('display', {}).get(
            'styles', [])
        try:
            style_definition = find_item(
                style_definitions, 'uri', request.environ['PATH_INFO'])
        except StopIteration:
            raise HTTPNotFound
        path = join(automation_definition['folder'], style_definition['path'])
        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

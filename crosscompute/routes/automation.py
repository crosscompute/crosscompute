# TODO: Show runs with command line option
# TODO: Let user customize root template
# TODO: Add unit tests
import json
from invisibleroads_macros_disk import make_random_folder
from os.path import basename, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    ID_LENGTH,
    MODE_ROUTE,
    RUN_ROUTE,
    STYLE_ROUTE)
from ..exceptions import CrossComputeDataError
from ..macros.iterable import find_item
from ..routines.configuration import (
    get_css_uris,
    get_variable_definitions)
from ..routines.variable import (
    parse_data_by_id)


class AutomationRoutes():

    def __init__(
            self, automation_definitions, automation_queue, timestamp_object):
        self.automation_definitions = automation_definitions
        self.automation_queue = automation_queue
        self._timestamp_object = timestamp_object

    def includeme(self, config):
        config.include(self.configure_root)
        config.include(self.configure_styles)
        config.include(self.configure_automations)
        config.include(self.configure_batches)
        config.include(self.configure_runs)

    def configure_root(self, config):
        config.add_route('root', '/')

        config.add_view(
            self.see_root,
            route_name='root',
            renderer='crosscompute:templates/root.jinja2')

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

    def configure_automations(self, config):
        config.add_route(
            'automation.json',
            AUTOMATION_ROUTE + '.json')
        config.add_route(
            'automation',
            AUTOMATION_ROUTE)

        config.add_view(
            self.run_automation,
            route_name='automation.json',
            renderer='json')
        config.add_view(
            self.see_automation,
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')

    def configure_batches(self, config):
        config.add_route(
            'automation batch',
            AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch mode',
            AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE)
        config.add_route(
            'automation batch mode file',
            AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE + FILE_ROUTE)

    def configure_runs(self, config):
        config.add_route(
            'automation run',
            AUTOMATION_ROUTE + RUN_ROUTE)
        config.add_route(
            'automation run mode',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE)
        config.add_route(
            'automation run mode file',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE + FILE_ROUTE)

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
            'timestamp_value': self._timestamp_object.value,
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

    def run_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        variable_definitions = get_variable_definitions(
            automation_definition, 'input')
        try:
            data_by_id = dict(request.params) or request.json_body
        except json.JSONDecodeError:
            data_by_id = {}
        try:
            data_by_id = parse_data_by_id(data_by_id, variable_definitions)
        except CrossComputeDataError as e:
            raise HTTPBadRequest(e)
        runs_folder = join(automation_definition['folder'], 'runs')
        folder = make_random_folder(runs_folder, ID_LENGTH)
        self.automation_queue.put((automation_definition, {
            'folder': folder,
            'data_by_id': data_by_id,
        }))
        run_id = basename(folder)
        if 'runs' not in automation_definition:
            automation_definition['runs'] = []
        run_uri = RUN_ROUTE.format(run_slug=run_id)
        automation_definition['runs'].append({
            'name': run_id,
            'slug': run_id,
            'folder': folder,
            'uri': run_uri,
        })
        # TODO: Change target page depending on definition
        return {'id': run_id}

    def see_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        css_uris = get_css_uris(automation_definition)
        return automation_definition | {
            'css_uris': css_uris,
            'timestamp_value': self._timestamp_object.value,
        }

    def get_automation_definition_from(self, request):
        matchdict = request.matchdict
        automation_slug = matchdict['automation_slug']
        try:
            automation_definition = find_item(
                self.automation_definitions, 'slug', automation_slug,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        return automation_definition

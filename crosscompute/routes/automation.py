# TODO: Show runs with command line option
# TODO: Let user customize root template
# TODO: Add unit tests
import json
from invisibleroads_macros_disk import make_random_folder
from itertools import count
from logging import getLogger
from os.path import basename, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse, Response

from ..constants import (
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    ID_LENGTH,
    MODE_NAME_BY_CODE,
    MODE_ROUTE,
    RUN_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_ROUTE)
from ..exceptions import CrossComputeDataError
from ..macros.iterable import extend_uniquely, find_item
from ..macros.web import get_html_from_markdown
from ..routines.configuration import (
    get_css_uris,
    get_template_texts,
    get_variable_definitions,
    parse_data_by_id)
from ..routines.variable import (
    VariableElement,
    VariableView,
    load_variable_data_from_folder,
    redact,
    save_variables)


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
            'automation batch mode variable',
            AUTOMATION_ROUTE + BATCH_ROUTE + MODE_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_mode,
            route_name='automation batch mode',
            renderer='crosscompute:templates/mode.jinja2')
        config.add_view(
            self.see_automation_batch_mode_variable,
            route_name='automation batch mode variable')

    def configure_runs(self, config):
        config.add_route(
            'automation run',
            AUTOMATION_ROUTE + RUN_ROUTE)
        config.add_route(
            'automation run mode',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE)
        config.add_route(
            'automation run mode variable',
            AUTOMATION_ROUTE + RUN_ROUTE + MODE_ROUTE + VARIABLE_ROUTE)

        config.add_view(
            self.see_automation_batch_mode,
            route_name='automation run mode',
            renderer='crosscompute:templates/mode.jinja2')
        config.add_view(
            self.see_automation_batch_mode_variable,
            route_name='automation run mode variable')

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
            'folder': folder, 'data_by_id': data_by_id}))
        run_id = basename(folder)
        run_uri = RUN_ROUTE.format(run_slug=run_id)
        if 'runs' not in automation_definition:
            automation_definition['runs'] = []
        automation_definition['runs'].append({
            'name': run_id, 'slug': run_id, 'folder': folder, 'uri': run_uri})
        save_variables(folder, {'input': redact(
            data_by_id, variable_definitions)})
        # TODO: Change target page depending on definition
        return {'id': run_id}

    def see_automation(self, request):
        automation_definition = self.get_automation_definition_from(request)
        css_uris = get_css_uris(automation_definition)
        return automation_definition | {
            'css_uris': css_uris,
            'timestamp_value': self._timestamp_object.value,
        }

    def see_automation_batch_mode(self, request):
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        absolute_batch_folder = join(automation_folder, batch_definition[
            'folder'])
        mode_name = self.get_mode_name_from(request)
        css_uris = get_css_uris(automation_definition)
        template_text = '\n'.join(get_template_texts(
            automation_definition, mode_name))
        variable_definitions = get_variable_definitions(
            automation_definition, mode_name, with_all=True)
        request_path = request.path
        for_print = 'p' in request.params
        return {
            'automation_definition': automation_definition,
            'batch_definition': batch_definition,
            'uri': request_path,
            'mode_name': mode_name,
            'timestamp_value': self._timestamp_object.value,
        } | render_mode_dictionary(
            mode_name, template_text, variable_definitions,
            absolute_batch_folder, css_uris, request_path, for_print)

    def see_automation_batch_mode_variable(self, request):
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        mode_name = self.get_mode_name_from(request)
        variable_definitions = get_variable_definitions(
            automation_definition, mode_name)
        matchdict = request.matchdict
        variable_id = matchdict['variable_id']
        try:
            variable_definition = find_item(
                variable_definitions, 'id', variable_id,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        absolute_batch_folder = join(
            automation_folder, batch_definition['folder'])
        variable_path = variable_definition['path']
        try:
            variable_data = load_variable_data_from_folder(
                absolute_batch_folder, mode_name, variable_path,
                self.variable_id)
        except CrossComputeDataError:
            raise HTTPNotFound
        if isinstance(variable_data, dict):
            if 'path' not in variable_data:
                raise HTTPBadRequest
            return FileResponse(variable_data['path'], request=request)
        return Response(variable_data)

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

    def get_batch_definition_from(self, request, automation_definition):
        matchdict = request.matchdict
        if 'batch_slug' in matchdict:
            slug = matchdict['batch_slug']
            key = 'batches'
        else:
            slug = matchdict['run_slug']
            key = 'runs'
        try:
            batch_definition = find_item(automation_definition.get(
                key, []), 'slug', slug)
        except StopIteration:
            raise HTTPNotFound
        return batch_definition

    def get_mode_name_from(self, request):
        matchdict = request.matchdict
        mode_code = matchdict['mode_code']
        try:
            mode_name = MODE_NAME_BY_CODE[mode_code]
        except KeyError:
            raise HTTPNotFound
        return mode_name


def render_mode_dictionary(
        mode_name, template_text, variable_definitions, absolute_batch_folder,
        css_uris, request_path, for_print):
    m = {'css_uris': css_uris.copy(), 'js_uris': [], 'js_texts': []}
    i = count()

    def render_html(match):
        matching_text, terms = match.group(0), match.group(1).split('|')
        variable_id = terms[0].strip()
        try:
            d = find_item(variable_definitions, 'id', variable_id)
        except StopIteration:
            L.warning('%s in template but not in configuration', variable_id)
            return matching_text
        view = VariableView.get_from(d).load(absolute_batch_folder)
        rendered_element = view.render(VariableElement(
            f'v{next(i)}', mode_name, terms[1:],
            f'{request_path}/{variable_id}', for_print))
        for k, v in m.items():
            extend_uniquely(v, rendered_element[k])
        return rendered_element['body_text']

    return m | {
        'body_text': get_html_from_markdown(VARIABLE_ID_PATTERN.sub(
            render_html, template_text)),
        'js_text': '\n'.join(m['js_texts']),
    }


L = getLogger(__name__)

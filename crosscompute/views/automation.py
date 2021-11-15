# TODO: Let user set automation slug in configuration file
# TODO: Let user set batch name and slug
# TODO: List links for all automations
# TODO: Let user customize homepage title
# TODO: Add tests
# TODO: Validate variable definitions for id and view


import logging
from markdown import markdown
from os.path import basename, exists, join
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FILE_ROUTE,
    HOME_ROUTE,
    REPORT_ROUTE,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN,
    VARIABLE_TYPE_NAME_BY_LETTER)
from ..macros import (
    find_item,
    get_slug_from_name,
    is_path_in_folder)


class AutomationViews():

    def __init__(self, configuration, configuration_folder):
        self.configuration = configuration
        self.configuration_folder = configuration_folder
        # TODO: Consider moving rest to a separate function
        automation_definitions = []
        automation_name = configuration.get(
            'name', AUTOMATION_NAME.format(automation_index=0))
        automation_slug = get_slug_from_name(automation_name)
        automation_uri = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)

        batch_definitions = []
        for batch_definition in configuration.get('batches', []):
            try:
                batch_folder = batch_definition['folder']
            except KeyError:
                logging.error('folder required for each batch')
                continue
            batch_name = batch_definition.get('name', basename(batch_folder))
            batch_slug = get_slug_from_name(batch_name)
            batch_uri = BATCH_ROUTE.format(batch_slug=batch_slug)
            batch_definitions.append({
                'name': batch_name,
                'slug': batch_slug,
                'uri': batch_uri,
                'folder': batch_folder,
            })

        automation_definitions.append({
            'name': automation_name,
            'slug': automation_slug,
            'uri': automation_uri,
            'batches': batch_definitions,
        })
        self.automation_definitions = automation_definitions
        self.style_definitions = self.get_style_definitions()

    def includeme(self, config):
        config.include(self.configure_styles_and_scripts)

        config.add_route('home', HOME_ROUTE)
        config.add_route('automation', AUTOMATION_ROUTE)
        config.add_route('automation batch', AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch report',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE)
        config.add_route(
            'automation batch report file',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE + FILE_ROUTE)

        config.add_view(
            self.see_home,
            route_name='home',
            renderer='crosscompute:templates/home.jinja2')
        config.add_view(
            self.see_automation,
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')
        config.add_view(
            self.see_automation_batch,
            route_name='automation batch',
            renderer='crosscompute:templates/batch.jinja2')
        config.add_view(
            self.see_automation_batch_report,
            route_name='automation batch report',
            renderer='crosscompute:templates/live.jinja2')
        config.add_view(
            self.see_automation_batch_report_file,
            route_name='automation batch report file')

    def configure_styles_and_scripts(self, config):
        if self.style_definitions:
            config.add_route('style', STYLE_ROUTE)
            config.add_view(
                self.see_style,
                route_name='style')

        script_definitions = []

        def update_renderer_globals():
            renderer_environment = config.get_jinja2_environment()
            renderer_environment.globals.update({
                'styles': self.style_definitions,
                'scripts': script_definitions,
                'HOME_ROUTE': HOME_ROUTE,
            })

        config.action(None, update_renderer_globals)

    def see_style(self, request):
        matchdict = request.matchdict
        style_path = matchdict['style_path']
        try:
            find_item(self.style_definitions, 'path', style_path)
        except StopIteration:
            raise HTTPNotFound

        folder = self.configuration_folder
        path = join(folder, style_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest

        try:
            response = FileResponse(path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def see_home(self, request):
        return {
            'automations': self.automation_definitions,
        }

    def see_automation(self, request):
        return self.get_automation_definition_from(request)

    def see_automation_batch(self, request):
        return {}

    def see_automation_batch_report(self, request):
        variable_type_name = self.get_variable_type_name_from(request)
        variable_definitions = self.get_variable_definitions(
            variable_type_name)
        template_texts = self.get_template_texts(variable_type_name)

        def render_variable_from(match):
            replacement_text = matching_text = match.group(0)
            variable_id = match.group(1)
            try:
                variable_definition = find_item(
                    variable_definitions, 'id', variable_id)
            except StopIteration:
                logging.warning(
                    '%s specified in template but missing in configuration',
                    variable_id)
                return matching_text
            variable_view = variable_definition['view']

            if variable_type_name == 'input':
                if variable_view == 'number':
                    # TODO: Load variable data from batch folder
                    variable_data = variable_definition.get('data', '')
                    replacement_text = (
                        f'<input type="number" class="input {variable_id}" '
                        f'value="{variable_data}">')
            elif variable_type_name == 'output':
                if variable_view == 'image':
                    # TODO: Split into crosscompute-image
                    variable_path = variable_definition['path']
                    image_uri = request.path + '/' + variable_path
                    replacement_text = f'<img src="{image_uri}">'
                elif variable_view == 'map-mapbox':
                    variable_path = variable_definition['path']
                    # consider adding style
                    # add script
                    # add div
                    # populate options into script
                    # replacement_text = f''
            return replacement_text

        report_markdown = VARIABLE_ID_PATTERN.sub(
            render_variable_from, '\n'.join(template_texts))
        report_content = markdown(report_markdown)
        return {
            'body_content': report_content,
        }

    def see_automation_batch_report_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        batch_definition = self.get_batch_definition_from(
            request, automation_definition)
        variable_type_name = self.get_variable_type_name_from(request)
        variable_definitions = self.get_variable_definitions(
            variable_type_name)
        variable_path = matchdict['variable_path']
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        logging.debug(variable_definition)
        batch_folder = batch_definition['folder']
        variable_folder = join(batch_folder, variable_type_name)
        folder = join(self.configuration_folder, variable_folder)
        path = join(folder, variable_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest
        return FileResponse(path, request=request)

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
        batch_slug = matchdict['batch_slug']
        try:
            batch_definition = find_item(
                automation_definition['batches'], 'slug',
                batch_slug, normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        return batch_definition

    def get_variable_type_name_from(self, request):
        matchdict = request.matchdict
        variable_type_letter = matchdict['variable_type']
        try:
            variable_type_name = VARIABLE_TYPE_NAME_BY_LETTER[
                variable_type_letter]
        except KeyError:
            raise HTTPBadRequest
        return variable_type_name

    def get_style_definitions(self):
        display_configuration = self.configuration.get('display', {})
        style_definitions = []
        for style_definition in display_configuration.get('styles', []):
            uri = style_definition.get('uri', '').strip()
            path = style_definition.get('path', '').strip()

            if uri:
                if path:
                    pass
                elif not uri.startswith('//') and uri.startswith(HOME_ROUTE):
                    path = uri.removeprefix(HOME_ROUTE)
            else:
                if path:
                    uri = STYLE_ROUTE.format(style_path=path)
                else:
                    logging.error('uri or path required for each style')
                    continue

            d = {'uri': uri}
            if path:
                if not path.endswith('.css'):
                    logging.warning('style path should end with .css')
                elif not exists(join(self.configuration_folder, path)):
                    logging.error('style not found at path %s', path)
                d['path'] = path
            style_definitions.append(d)
        return style_definitions

    def get_variable_definitions(self, variable_type_name):
        return self.configuration.get(
            variable_type_name, {}).get('variables', [])

    def get_template_definitions(self, variable_type_name):
        return self.configuration.get(
            variable_type_name, {}).get('templates', [])

    def get_template_texts(self, variable_type_name):
        template_definitions = self.get_template_definitions(
            variable_type_name)
        template_paths = [
            _['path'] for _ in template_definitions if 'path' in _]
        if template_paths:
            template_texts = [open(join(
                self.configuration_folder, _,
            ), 'rt').read() for _ in template_paths]
        else:
            variable_definitions = self.get_variable_definitions(
                variable_type_name)
            variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
            template_texts = [' '.join('{' + _ + '}' for _ in variable_ids)]
        return template_texts

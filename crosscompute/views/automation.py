# TODO: Let user set automation slug in configuration file
# TODO: Let user set batch name and slug
# TODO: List links for all automations
# TODO: Let user customize homepage title
# TODO: Add tests


import logging
from os.path import basename, join
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
    VARIABLE_TYPE_NAMES)
from ..macros import (
    find_item,
    get_slug_from_name,
    is_path_in_folder)


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
        self.script_urls = []

        # TODO: Consider moving to a separate function
        automation_dictionaries = []
        automation_name = configuration.get(
            'name', AUTOMATION_NAME.format(automation_index=0))
        automation_slug = get_slug_from_name(automation_name)
        automation_url = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)

        batch_dictionaries = []
        batch_definitions = configuration.get('batches', [])
        for batch_definition in batch_definitions:
            try:
                batch_folder = batch_definition['folder']
            except KeyError:
                logging.warning('folder required for each batch')
                continue
            batch_name = batch_definition.get('name', basename(batch_folder))
            batch_slug = get_slug_from_name(batch_name)
            batch_url = BATCH_ROUTE.format(batch_slug=batch_slug)
            batch_dictionaries.append({
                'name': batch_name,
                'slug': batch_slug,
                'url': batch_url,
                'folder': batch_folder,
            })

        automation_dictionaries.append({
            'name': automation_name,
            'slug': automation_slug,
            'url': automation_url,
            'batches': batch_dictionaries,
        })
        self.automation_dictionaries = automation_dictionaries

    def includeme(self, config):
        config.include(self.configure_stylesheets)

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
                'HOME_ROUTE': HOME_ROUTE,
                'style': {'urls': self.style_urls},
                'script': {'urls': self.script_urls},
            })

        config.action(None, update_renderer_globals)

    def see_style(self, request):
        style_path = self.style_path
        try:
            response = FileResponse(style_path, request)
        except TypeError:
            raise HTTPNotFound
        return response

    def see_home(self, request):
        return {
            'automations': self.automation_dictionaries,
        }

    def see_automation(self, request):
        matchdict = request.matchdict
        automation_slug = matchdict['automation_slug']
        try:
            automation_dictionary = find_item(
                self.automation_dictionaries, 'slug', automation_slug,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        return automation_dictionary

    def see_automation_batch(self, request):
        return {}

    def see_automation_batch_report(self, request):
        return {
            'body_content': 'whee',
        }

    def see_automation_batch_report_file(self, request):
        matchdict = request.matchdict
        automation_slug = matchdict['automation_slug']
        batch_slug = matchdict['batch_slug']
        variable_type = matchdict['variable_type']
        variable_path = matchdict['variable_path']
        try:
            automation_dictionary = find_item(
                self.automation_dictionaries, 'slug',
                automation_slug, normalize=str.casefold)
            batch_dictionary = find_item(
                automation_dictionary['batches'], 'slug',
                batch_slug, normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        try:
            variable_type_name = find_item(
                VARIABLE_TYPE_NAMES, 0, variable_type, normalize=str.casefold)
        except StopIteration:
            raise HTTPBadRequest
        variable_definitions = self.configuration.get(
            variable_type_name, {}).get('variables', [])
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        logging.debug(variable_definition)
        batch_folder = batch_dictionary['folder']
        variable_folder = join(batch_folder, variable_type_name)
        folder = join(self.configuration_folder, variable_folder)
        path = join(folder, variable_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest
        return FileResponse(path, request=request)

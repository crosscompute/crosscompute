# TODO: Let user set automation slug in configuration file
# TODO: Let user set batch name and slug
# TODO: List links for all automations
# TODO: Let user customize homepage title
# TODO: Screen variable path if it does not exist in configuration
# TODO: Sanitize variable path for security
# TODO: Test with and without request for FileResponse
# TODO: Run server in separate thread
import re
from argparse import ArgumentParser
from markdown import markdown
from os.path import basename, join, normpath
from pyramid.config import Configurator
from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPNotFound)
from pyramid.response import FileResponse
from waitress import serve

from crosscompute import Automation
from crosscompute.macros import normalize_key
from crosscompute.routines import (
    configure_argument_parser_for_logging,
    configure_logging_from)


AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
REPORT_ROUTE = '/{variable_type}'
FILE_ROUTE = '/{variable_path}'
STYLE_ROUTE = '/style.css'
VARIABLE_TYPES = 'i', 'o', 'l', 'd'
VARIABLE_ID_PATTERN = re.compile(r'{\s*([^}]+?)\s*}')


def get_slug_from_name(name):
    return normalize_key(name, word_separator='-')


def find_dictionary(dictionaries, key, value):

    def is_match(v):
        return v.casefold() == value.casefold()

    return next(filter(lambda item: is_match(item[key]), dictionaries))


if __name__ == '__main__':
    a = ArgumentParser()
    a.add_argument('--host', default='127.0.0.1')
    a.add_argument('--port', default='7000')
    a.add_argument('configuration_path')
    configure_argument_parser_for_logging(a)
    args = a.parse_args()

    configure_logging_from(args)

    automation = Automation.load(args.configuration_path)
    configuration = automation.configuration
    configuration_folder = automation.configuration_folder

    batch_dictionaries = []
    batch_definitions = configuration['batches']
    for batch_definition in batch_definitions:
        batch_folder = batch_definition['folder']
        batch_name = basename(batch_folder)
        batch_slug = get_slug_from_name(batch_name)
        batch_url = BATCH_ROUTE.format(batch_slug=batch_slug)
        batch_dictionaries.append({
            'name': batch_name,
            'url': batch_url,
        })

    automation_dictionaries = []
    automation_name = configuration['name']
    automation_slug = get_slug_from_name(automation_name)
    automation_url = AUTOMATION_ROUTE.format(automation_slug=automation_slug)
    automation_dictionaries.append({
        'name': automation_name,
        'url': automation_url,
        'batches': batch_dictionaries,
    })

    style_urls = []
    display_configuration = configuration.get('display', {})
    style_configuration = display_configuration.get('style', {})
    style_path = style_configuration.get('path')
    if style_path:
        style_urls.append(STYLE_ROUTE)

    def see_home(request):
        return {
            'automations': automation_dictionaries,
            # 'style': {'urls': style_urls},
        }

    def see_style(request):
        if not style_path:
            raise HTTPNotFound
        return FileResponse(style_path, request)

    def see_automation(request):
        return find_dictionary(automation_dictionaries, 'url', request.path)

    def see_automation_batch(request):
        return {}

    def see_automation_batch_report(request):
        # TODO: Fix temporary code
        matchdict = request.matchdict
        batch_slug = matchdict['batch_slug']
        for batch_definition in batch_definitions:
            batch_folder = batch_definition['folder']
            batch_name = basename(batch_folder)
            if batch_slug == get_slug_from_name(batch_name):
                break
        else:
            raise HTTPNotFound

        variable_type = matchdict['variable_type']
        variable_type_name = {
            'i': 'input', 'o': 'output', 'l': 'log', 'd': 'debug',
        }[variable_type.lower()]

        variable_definitions = configuration[
            variable_type_name]['variables']
        '''
        variable_data_by_id = {
            _['id']: _['data'] for _ in batch_variable_definitions}
        '''
        variable_path_by_id = {
            _['id']: _['path'] for _ in variable_definitions}

        report_configuration = configuration[variable_type_name]
        template_path = join(
            configuration_folder,
            report_configuration['templates'][0]['path'])
        template_markdown = open(template_path, 'rt').read()
        # template_markdown = ' '.join(
        # '{' + _ + '}' for _ in input_variable_ids)

        def render_variable_from(match):
            matching_text = match.group(0)
            variable_id = match.group(1)
            try:
                # TODO: Do both output and input
                # variable_data = variable_data_by_id[variable_id]
                variable_path = variable_path_by_id[variable_id]
            except KeyError:
                print(variable_id, variable_path_by_id)
                print('UHOH')
                return matching_text
            '''
            replacement_text = "<input
                    class='input {variable_id}'
                    type='number' value='{variable_data}'>".format(
                variable_id=variable_id,
                variable_data=variable_data)
            '''
            image_url = request.path + '/' + variable_path
            replacement_text = f"<img src='{image_url}'>"
            return replacement_text

        report_markdown = VARIABLE_ID_PATTERN.sub(
            render_variable_from, template_markdown)
        report_content = markdown(report_markdown)
        return {
            'content': report_content,
            'style': {'urls': style_urls},
        }

    def see_automation_batch_report_file(request):
        matchdict = request.matchdict
        '''
        automation_dictionary = find_dictionary(
            automation_dictionaries, 'url', request.path)
        variable_type = matchdict['variable_type']
        if variable_type not in VARIABLE_TYPES:
            raise HTTPBadRequest
        '''
        # TODO: Fix temporary code
        batch_slug = matchdict['batch_slug']
        for batch_definition in batch_definitions:
            batch_folder = batch_definition['folder']
            batch_name = basename(batch_folder)
            if batch_slug == get_slug_from_name(batch_name):
                break
        else:
            raise HTTPNotFound
        batch_folder = batch_definition['folder']
        variable_type = matchdict['variable_type']
        variable_folder = {
            'i': join(batch_folder, 'input'),
            'o': join(batch_folder, 'output'),
            'l': join(batch_folder, 'log'),
            'd': join(batch_folder, 'debug'),
        }[variable_type]
        variable_path = matchdict['variable_path']
        path = join(configuration_folder, variable_folder, variable_path)
        # TODO: Make more robust
        if not normpath(path).startswith(join(
                configuration_folder, variable_folder)):
            print(path)
            print(configuration_folder, variable_folder)
            raise HTTPBadRequest
        return FileResponse(path, request=request)

    # automation.serve()

    with Configurator(settings={
        'jinja2.globals': {'style': {'urls': style_urls}},
    }) as config:
        config.include('pyramid_jinja2')

        config.add_route('home', '/')
        config.add_route('style', STYLE_ROUTE)
        config.add_route('automation', AUTOMATION_ROUTE)
        config.add_route('automation batch', AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch report',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE)
        config.add_route(
            'automation batch report file',
            AUTOMATION_ROUTE + BATCH_ROUTE + REPORT_ROUTE + FILE_ROUTE)

        config.add_view(
            see_home,
            route_name='home',
            renderer='crosscompute:templates/home.jinja2')
        config.add_view(
            see_style,
            route_name='style')
        config.add_view(
            see_automation,
            route_name='automation',
            renderer='crosscompute:templates/automation.jinja2')
        config.add_view(
            see_automation_batch,
            route_name='automation batch',
            renderer='crosscompute:templates/batch.jinja2')
        config.add_view(
            see_automation_batch_report,
            route_name='automation batch report',
            renderer='crosscompute:templates/base.jinja2')
        config.add_view(
            see_automation_batch_report_file,
            route_name='automation batch report file')

    app = config.make_wsgi_app()
    serve(app, host=args.host, port=args.port)

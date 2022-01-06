# TODO: Let creator override mapbox js


from ..macros import (
    extend_uniquely,
    is_path_in_folder,
    make_unique_folder)
from ..routines.configuration import (
    VariableView,
    apply_functions,
    get_all_variable_definitions,
    get_css_uris,
    get_raw_variable_definitions,
    get_template_texts,
    get_variable_configuration,
    load_variable_data,
    parse_data_by_id)
from ..routines.web import get_html_from_markdown


L = getLogger(__name__)


        config.add_view(
            self.see_automation_result_section,
            route_name='automation batch section',
            renderer='crosscompute:templates/page.jinja2')
        config.add_view(
            self.see_automation_result_section_file,
            route_name='automation batch section file')
        config.add_view(
            self.see_automation_page,
            route_name='automation run page',
            renderer='crosscompute:templates/page.jinja2')
        config.add_view(
            self.see_automation_page_file,
            route_name='automation run page file')

    def see_automation_batch(self, request):
        return {}

    # def see_automation_result_page(self, request):
    # def see_automation_batch_mode
    def see_automation_page(self, request):
        page_type_name = self.get_page_type_name_from(request)
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        result_definition = self.get_result_definition_from(
            request, automation_definition)
        result_folder = join(automation_folder, result_definition['folder'])
        variable_definitions = get_all_variable_definitions(
            automation_definition, page_type_name)
        template_texts = get_template_texts(
            automation_definition, page_type_name)
        css_uris = get_css_uris(automation_definition)
        page_text = '\n'.join(template_texts)
        return {
            'automation_definition': automation_definition,
            'result_definition': result_definition,
            'uri': request.path,
            'page_type_name': page_type_name,
            'timestamp_value': self.timestamp_object.value,
        } | render_page_dictionary(
            request, css_uris, page_text, variable_definitions, result_folder)

    def see_automation_page_file(self, request):
        matchdict = request.matchdict
        automation_definition = self.get_automation_definition_from(request)
        automation_folder = automation_definition['folder']
        result_definition = self.get_result_definition_from(
            request, automation_definition)
        page_type_name = self.get_page_type_name_from(request)
        variable_definitions = get_raw_variable_definitions(
            automation_definition, page_type_name)
        variable_path = matchdict['variable_path']
        try:
            variable_definition = find_item(
                variable_definitions, 'path', variable_path,
                normalize=str.casefold)
        except StopIteration:
            raise HTTPNotFound
        L.debug(variable_definition)
        folder = join(automation_folder, result_definition[
            'folder'], page_type_name)
        path = join(folder, variable_path)
        if not is_path_in_folder(path, folder):
            raise HTTPBadRequest
        return FileResponse(path, request=request)

    def get_result_definition_from(self, request, automation_definition):
        matchdict = request.matchdict
        if 'run_slug' in matchdict:
            slug = matchdict['run_slug']
            key = 'runs'
        else:
            slug = matchdict['batch_slug']
            key = 'batches'
        try:
            page_definition = find_item(automation_definition.get(
                key, []), 'slug', slug)
        except StopIteration:
            raise HTTPNotFound
        return page_definition

    def get_page_type_name_from(self, request):
        matchdict = request.matchdict
        page_type_letter = matchdict['page_type']
        try:
            page_type_name = PAGE_TYPE_NAME_BY_LETTER[
                page_type_letter]
        except KeyError:
            raise HTTPBadRequest
        return page_type_name


def render_page_dictionary(
        request, css_uris, page_text, variable_definitions,
        absolute_folder):
    css_uris, js_uris, js_texts, variable_index = css_uris.copy(), [], [], 0

    def render_html(match):
        matching_text = match.group(0)
        expression_terms = match.group(1).split('|')
        variable_id = expression_terms[0].strip()
        try:
            d = find_item(variable_definitions, 'id', variable_id)
        except StopIteration:
            L.warning('%s in template but not in configuration', variable_id)
            return matching_text
        variable_view = VariableView.load_from(d)
        variable_path, variable_type_name = d['path'], d['type']
        page_folder = join(folder, variable_type_name)

        if variable_view.is_asynchronous or variable_path == 'ENVIRONMENT':
            variable_data = ''
        else:
            variable_data = apply_functions(load_variable_data(join(
                page_folder, variable_path,
            ), variable_id), expression_terms[1:], FUNCTION_BY_NAME)

        variable_configuration = get_variable_configuration(d, page_folder)
        nonlocal variable_index
        variable_element = variable_view.render(
            f'v{variable_index}',
            variable_data, variable_configuration, request.path)
        variable_index += 1
        extend_uniquely(css_uris, variable_element['css_uris'])
        extend_uniquely(js_uris, variable_element['js_uris'])
        extend_uniquely(js_texts, variable_element['js_texts'])
        return variable_element['body_text']

    return {
        'css_uris': css_uris,
        'js_uris': js_uris,
        'body_text': get_html_from_markdown(VARIABLE_ID_PATTERN.sub(
            render_html, page_text)),
        'js_text': '\n'.join(js_texts),
    }

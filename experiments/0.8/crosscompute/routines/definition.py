def normalize_result_definition(raw_result_definition, folder=None):
    if 'path' in raw_result_definition:
        result_definition_path = join(folder, raw_result_definition['path'])
        result_definition = load_definition(result_definition_path, kinds=['result'])
    else:
        result_definition = {'kind': 'result'}

    result_name = raw_result_definition.get(
        'name', result_definition.get('name', ''))
    if result_name:
        result_definition['name'] = result_name

    tool_definition = dict(raw_result_definition.get(
        'tool', result_definition.get('tool', {})))
    # TODO: Load tool by name
    if 'id' in tool_definition:
        tool_id = tool_definition['id']
        tool_version_id = get_nested_value(
            tool_definition, 'version', 'id', default_value='latest')
        tool_definition = fetch_resource(
            'tools', tool_id + '/versions/' + tool_version_id)
    elif 'path' in tool_definition:
        tool_definition_path = join(folder, tool_definition['path'])
        tool_definition = load_definition(tool_definition_path)
    result_definition['tool'] = tool_definition

    raw_variable_dictionaries = sum([
        get_nested_value(result_definition, 'input', 'variables', []),
        get_nested_value(raw_result_definition, 'input', 'variables', []),
    ], [])
    variable_definitions = get_nested_value(
        tool_definition, 'input', 'variables', [])
    result_definition['input'] = {
        'variables': normalize_result_variable_dictionaries(
            raw_variable_dictionaries, variable_definitions, folder)}

    if 'print' in raw_result_definition:
        result_definition['print'] = get_print_dictionary(
            raw_result_definition['print'], folder)
    return result_definition


def normalize_data(raw_data, view_name, variable_id=None, folder=None):
    is_dictionary = isinstance(raw_data, dict)
    is_list = isinstance(raw_data, list)
    if not is_dictionary and not is_list:
        raise CrossComputeDefinitionError({
            'data': 'must be a dictionary or list'})
    if is_list:
        data = [normalize_data_dictionary(
            _, view_name, variable_id, folder) for _ in raw_data]
    elif folder is not None and 'batch' in raw_data:
        batch_dictionary = normalize_batch_dictionary(raw_data['batch'])
        batch_path = batch_dictionary['path']
        try:
            batch_file = open(join(folder, batch_path))
        except IOError:
            raise CrossComputeDefinitionError({
                'path': f'is bad for {batch_path}'})
        data = [{
            'value': normalize_value(_.strip(), view_name),
        } for _ in batch_file]
    else:
        data = normalize_data_dictionary(
            raw_data, view_name, variable_id, folder)
    return data


def normalize_data_dictionary(
        raw_data_dictionary, view_name, variable_id=None, folder=None):
    check_dictionary(raw_data_dictionary, 'data')
    has_value = 'value' in raw_data_dictionary
    has_dataset = 'dataset' in raw_data_dictionary
    has_file = 'file' in raw_data_dictionary
    has_path = folder is not None and 'path' in raw_data_dictionary
    if not has_value and not has_dataset and not has_file and not has_path:
        raise CrossComputeDefinitionError({
            'data': 'must have value or dataset or file or path'})
    data_dictionary = {}
    if has_value:
        data_dictionary['value'] = normalize_value(
            raw_data_dictionary['value'], view_name)
    elif has_dataset:
        data_dictionary['dataset'] = normalize_dataset_dictionary(
            raw_data_dictionary['dataset'])
    elif has_file:
        data_dictionary['file'] = normalize_file_dictionary(
            raw_data_dictionary['file'])
    elif has_path:
        data_path = join(folder, raw_data_dictionary['path'])
        file_extension = splitext(data_path)[1]
        load = define_load(view_name, file_extension)
        data_dictionary['value'] = load(data_path, variable_id)
    return data_dictionary


def normalize_report_variable_dictionaries(
        raw_variable_dictionaries, folder=None):
    check_list(raw_variable_dictionaries, 'variables')
    raw_variable_dictionary_by_id = get_variable_dictionary_by_id(
        raw_variable_dictionaries)
    variable_dictionaries = []
    for (
        variable_id, raw_variable_dictionary,
    ) in raw_variable_dictionary_by_id.items():
        try:
            variable_view = raw_variable_dictionary['view']
            variable_data = raw_variable_dictionary['data']
        except KeyError as e:
            raise CrossComputeDefinitionError({
                e.args[0]: 'is required for each report variable'})
        variable_data = normalize_data(
            variable_data, variable_view, variable_id, folder)
        variable_dictionaries.append({
            'id': variable_id, 'view': variable_view, 'data': variable_data})
    return variable_dictionaries


def normalize_result_variable_dictionaries(
        raw_variable_dictionaries, variable_definitions, folder=None):
    check_list(raw_variable_dictionaries, 'variables')
    raw_variable_dictionary_by_id = get_variable_dictionary_by_id(
        raw_variable_dictionaries)
    variable_definition_by_id = {_['id']: _ for _ in variable_definitions}
    variable_dictionaries = []
    for (
        variable_id, raw_variable_dictionary,
    ) in raw_variable_dictionary_by_id.items():
        try:
            variable_definition = variable_definition_by_id[variable_id]
        except KeyError:
            raise CrossComputeDefinitionError({
                'id': 'could not find variable ' + variable_id
                + ' in tool definition'})
        variable_view = variable_definition['view']
        try:
            variable_data = raw_variable_dictionary['data']
        except KeyError:
            raise CrossComputeDefinitionError({
                'data': 'is required for each result variable'})
        variable_data = normalize_data(
            variable_data, variable_view, variable_id, folder)
        variable_dictionaries.append({
            'id': variable_id, 'data': variable_data})
    return variable_dictionaries


def normalize_report_template_dictionaries(
        raw_template_dictionaries, folder=None):
    # TODO: Support report markdown templates
    template_dictionaries = []
    for raw_template_dictionary in raw_template_dictionaries:
        try:
            template_path = raw_template_dictionary['path']
        except KeyError:
            raise CrossComputeDefinitionError({'path': 'is required'})
        file_extension = splitext(template_path)[1]
        if file_extension == '.yml':
            template_definition = load_definition(join(
                folder, template_path), kinds=['report', 'result'])
            template_dictionaries.append(template_definition)
        elif file_extension == '.md':
            raise CrossComputeImplementationError({
                'path': 'is not yet implemented for markdown templates'})
        else:
            raise CrossComputeDefinitionError({
                'path': 'has unsupported extension ' + file_extension})
    return template_dictionaries


def normalize_tool_template_dictionaries(
        raw_template_dictionaries, variable_dictionaries, folder=None):
    template_dictionaries = []
    for template_index, raw_template_dictionary in enumerate(
            raw_template_dictionaries):
        template_id = raw_template_dictionary.get('id', str(template_index))
        block_dictionaries = get_template_block_dictionaries(
            raw_template_dictionary, variable_dictionaries, folder)
        if not block_dictionaries:
            continue
        template_dictionaries.append({
            'id': template_id,
            'name': raw_template_dictionary.get('name') or get_name_from_id(
                template_id),
            'blocks': block_dictionaries,
        })
    if not template_dictionaries and variable_dictionaries:
        template_dictionaries.append({
            'id': 'generated',
            'name': 'Generated',
            'blocks': [{'id': _['id']} for _ in variable_dictionaries],
        })
    return template_dictionaries


def normalize_test_dictionaries(raw_test_dictionaries):
    check_list(raw_test_dictionaries, 'tests')
    if not raw_test_dictionaries:
        raise CrossComputeDefinitionError({
            'tests': 'must have at least one test defined'})
    try:
        test_dictionaries = [{
            'folder': _['folder'],
        } for _ in raw_test_dictionaries]
    except TypeError:
        raise CrossComputeDefinitionError({
            'tests': 'must be a list of dictionaries'})
    except KeyError as e:
        raise CrossComputeDefinitionError({
            e.args[0]: 'is required for each test'})
    return test_dictionaries


def normalize_environment_dictionary(raw_environment_dictionary):
    d = {}
    try:
        d.update({
            'image': raw_environment_dictionary['image'],
            'processor': raw_environment_dictionary['processor'],
            'memory': raw_environment_dictionary['memory'],
        })
    except KeyError as e:
        raise CrossComputeDefinitionError({
            'environment': 'requires ' + e.args[0]})
    if 'variables' in raw_environment_dictionary:
        d['variables'] = normalize_environment_variable_dictionaries(
            raw_environment_dictionary['variables'])
    return d


def normalize_block_dictionaries(raw_block_dictionaries, with_data=True):
    check_list(raw_block_dictionaries, 'blocks')
    block_dictionaries = []
    for raw_block_dictionary in raw_block_dictionaries:
        has_id = 'id' in raw_block_dictionary
        has_view = 'view' in raw_block_dictionary
        has_data = 'data' in raw_block_dictionary
        block_dictionary = {}
        if has_id:
            block_dictionary['id'] = raw_block_dictionary['id']
        if has_view:
            raw_view_name = raw_block_dictionary['view']
            view_name = normalize_view_name(raw_view_name)
            block_dictionary['view'] = view_name
        elif not has_id:
            raise CrossComputeDefinitionError({
                'view': 'is required if block lacks id'})
        if has_data:
            raw_data_dictionary = raw_block_dictionary['data']
            data_dictionary = normalize_data_dictionary(
                raw_data_dictionary, view_name)
            block_dictionary['data'] = data_dictionary
        elif with_data:
            message = 'is required for variable'
            if has_id:
                message += ' ' + block_dictionary['id']
            raise CrossComputeDefinitionError({'data': message})
        block_dictionaries.append(block_dictionary)
    return block_dictionaries


def get_print_dictionary(dictionary, folder):
    print_dictionary = {}

    if 'style' in dictionary:
        raw_style_definition = dictionary['style']
        if 'path' in raw_style_definition:
            style_path = join(folder, raw_style_definition['path'])
            style_rules = load_style_rule_strings(style_path)
        style_rules += normalize_style_rule_strings(raw_style_definition.get('rules', []))
        style_definition = {'rules': style_rules}
        print_dictionary['style'] = style_definition

    if 'header' in dictionary:
        raw_header_definition = dictionary['header']
        if 'path' in raw_header_definition:
            header_path = join(folder, raw_header_definition['path'])
            print_dictionary['header'] = load_markdown_html(header_path)

    if 'footer' in dictionary:
        raw_footer_definition = dictionary['footer']
        if 'path' in raw_footer_definition:
            footer_path = join(folder, raw_footer_definition['path'])
            print_dictionary['footer'] = load_markdown_html(footer_path)

    if 'format' in dictionary:
        raw_format = dictionary['format']
        if raw_format not in PRINT_FORMAT_NAMES:
            raise CrossComputeDefinitionError({
                'format': 'must be ' + ' or '.join(PRINT_FORMAT_NAMES)})
        print_dictionary['format'] = raw_format

    return print_dictionary


def get_template_block_dictionaries(
        dictionary, variable_dictionaries, folder=None):
    if 'blocks' in dictionary:
        raw_block_dictionaries = dictionary['blocks']
    elif 'path' in dictionary and folder is not None:
        template_path = join(folder, dictionary['path'])
        raw_block_dictionaries = load_block_dictionaries(
            template_path, variable_dictionaries)
    else:
        raw_block_dictionaries = []
    return normalize_block_dictionaries(
        raw_block_dictionaries, with_data=False)

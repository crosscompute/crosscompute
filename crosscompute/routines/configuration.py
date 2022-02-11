def get_variable_definitions(configuration, mode_name, with_all=False):
    mode_configuration = configuration.get(mode_name, {})
    variable_definitions = mode_configuration.get('variables', [])
    for variable_definition in variable_definitions:
        variable_definition['mode'] = mode_name
    if with_all:
        variable_definitions = variable_definitions.copy()
        for MODE_NAME in MODE_NAMES:
            if mode_name == MODE_NAME:
                continue
            variable_definitions.extend(get_variable_definitions(
                configuration, MODE_NAME))
    return variable_definitions


def get_template_texts(configuration, mode_name):
    template_texts = []
    folder = configuration.folder
    mode_configuration = configuration.get(mode_name, {})
    for template_definition in mode_configuration.get('templates', []):
        try:
            template_path = template_definition['path']
        except KeyError:
            L.error('path required for each template')
            continue
        try:
            path = join(folder, template_path)
            template_file = open(path, 'rt')
        except OSError:
            L.error('%s does not exist or is not accessible', path)
            continue
        template_text = template_file.read().strip()
        if not template_text:
            continue
        template_texts.append(template_text)
    if not template_texts:
        variable_definitions = configuration.get_variable_definitions(
            mode_name)
        variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
        template_texts = ['\n'.join('{%s}' % _ for _ in variable_ids)]
    return template_texts

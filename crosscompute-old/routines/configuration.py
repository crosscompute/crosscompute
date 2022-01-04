# TODO: Save to yaml, ini, toml
import csv
import json
import tomli
import yaml
from configparser import ConfigParser
from os import environ
from os.path import basename, dirname, exists, join, splitext
from string import Template
from time import time

from .. import __version__
from ..constants import (
    AUTOMATION_NAME,
    AUTOMATION_ROUTE,
    BATCH_ROUTE,
    FUNCTION_BY_NAME,
    PART_NAMES,
    STYLE_ROUTE,
    VARIABLE_ID_PATTERN)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeDataError,
    CrossComputeError)
from ..macros import (
    format_slug, get_environment_value, group_by, make_folder)


MAP_MAPBOX_CSS_URI = 'mapbox://styles/mapbox/dark-v10'
MAP_MAPBOX_JS_TEMPLATE = Template('''\
const $element_id = new mapboxgl.Map({
  container: '$element_id',
  style: '$style_uri',
  center: [$longitude, $latitude],
  zoom: $zoom,
  // preserveDrawingBuffer: true,
})
$element_id.on('load', () => {
  $element_id.addSource('$element_id', {
    type: 'geojson',
    data: '$data_uri'})
  $element_id.addLayer({
    id: '$element_id',
    type: 'fill',
    source: '$element_id'})
})''')
MAP_PYDECK_SCREENGRID_JS_TEMPLATE = Template('''\
const layers = []
layers.push(new deck.ScreenGridLayer({
  data: '$data_uri',
  getPosition: d => d,
  opacity: $opacity,
}))
new deck.DeckGL({
  container: '$element_id',
  mapboxApiAccessToken: '$mapbox_token',
  mapStyle: '$style_uri',
  initialViewState: {
    longitude: $longitude,
    latitude: $latitude,
    zoom: $zoom,
  },
  controller: true,
  layers,
  /*
  preserveDrawingBuffer: true,
  glOptions: {
    preserveDrawingBuffer: true,
  },
  */
})
''')


def load_configuration(configuration_path):
    configuration_format = get_configuration_format(configuration_path)
    load_raw_configuration = {
        'ini': load_raw_configuration_ini,
        'toml': load_raw_configuration_toml,
        'yaml': load_raw_configuration_yaml,
    }[configuration_format]
    configuration = load_raw_configuration(configuration_path)
    configuration['folder'] = dirname(configuration_path) or '.'
    configuration = validate_configuration(configuration)
    L.debug(f'{configuration_path} loaded')
    return configuration


def validate_configuration(configuration):
    if 'crosscompute' not in configuration:
        raise CrossComputeError('crosscompute expected')
    protocol_version = configuration['crosscompute']
    if protocol_version != __version__:
        raise CrossComputeConfigurationError(
            f'crosscompute {protocol_version} != {__version__}; '
            f'pip install crosscompute=={protocol_version}')
    for part_name in PART_NAMES:
        part_configuration = configuration.get(part_name, {})
        for variable_definition in part_configuration.get('variables', []):
            try:
                variable_definition['id']
                variable_definition['view']
                variable_definition['path']
            except KeyError as e:
                raise CrossComputeConfigurationError(
                    '%s required for each variable' % e)
    return configuration


def load_raw_configuration_ini(configuration_path):
    configuration = ConfigParser()
    configuration.read(configuration_path)
    return dict(configuration)


def load_raw_configuration_toml(configuration_path):
    with open(configuration_path, 'rt') as configuration_file:
        configuration = tomli.load(configuration_file)
    return configuration


def load_raw_configuration_yaml(configuration_path):
    try:
        with open(configuration_path, 'rt') as configuration_file:
            configuration = yaml.safe_load(configuration_file)
    except (OSError, yaml.parser.ParserError) as e:
        raise CrossComputeConfigurationError(e)
    return configuration or {}


def get_automation_definitions(configuration):
    automation_definitions = []
    for automation_index, automation_configuration in enumerate(
            get_automation_configurations(configuration)):
        if 'output' not in automation_configuration:
            continue
        automation_name = automation_configuration.get(
            'name', make_automation_name(automation_index))
        automation_slug = automation_configuration.get(
            'slug', format_slug(automation_name))
        automation_uri = AUTOMATION_ROUTE.format(
            automation_slug=automation_slug)
        automation_configuration['name'] = automation_name
        automation_configuration['slug'] = automation_slug
        automation_configuration['uri'] = automation_uri
        automation_configuration.update({
            'batches': get_batch_definitions(automation_configuration),
            'display': get_display_configuration(automation_configuration),
        })
        automation_definitions.append(automation_configuration)
    return automation_definitions


def get_automation_configurations(configuration):
    automation_configurations = []
    configurations = [configuration]
    while configurations:
        c = configurations.pop(0)
        folder = c['folder']
        for import_configuration in c.get('imports', []):
            if 'path' in import_configuration:
                path = import_configuration['path']
                automation_configuration = load_configuration(join(
                    folder, path))
            else:
                L.error(
                    'path or folder or uri or name required for each import')
                continue
            automation_configuration['parent'] = c
            configurations.append(automation_configuration)
        automation_configurations.append(c)
    return automation_configurations


def get_batch_definitions(configuration):
    batch_definitions = []
    automation_folder = configuration['folder']
    variable_definitions = get_raw_variable_definitions(
        configuration, 'input')
    for raw_batch_definition in configuration.get('batches', []):
        try:
            batch_definition = normalize_batch_definition(raw_batch_definition)
            if 'configuration' in raw_batch_definition:
                batch_configuration = raw_batch_definition['configuration']
                if 'path' in batch_configuration:
                    definitions = get_batch_definitions_from_path(join(
                        automation_folder, batch_configuration['path'],
                    ), batch_definition, variable_definitions)
                # TODO: Support batch_configuration['uri']
                else:
                    raise CrossComputeConfigurationError(
                        'path expected for each batch configuration')
            else:
                batch_slug = batch_definition['slug'] or format_slug(
                    batch_definition['name'])
                batch_definition['slug'] = batch_slug
                batch_definition['uri'] = BATCH_ROUTE.format(
                    batch_slug=batch_slug)
                definitions = [batch_definition]
        except CrossComputeConfigurationError as e:
            L.error(e)
            continue
        batch_definitions.extend(definitions)
    return batch_definitions


def normalize_batch_definition(raw_batch_definition):
    try:
        batch_folder = get_scalar_text(raw_batch_definition, 'folder')
    except KeyError:
        raise CrossComputeConfigurationError('folder required for each batch')
    batch_name = get_scalar_text(raw_batch_definition, 'name', basename(
        batch_folder))
    batch_slug = get_scalar_text(raw_batch_definition, 'slug', '')
    return {
        'folder': batch_folder,
        'name': batch_name,
        'slug': batch_slug,
    }


def get_batch_definitions_from_path(
        path, batch_definition, variable_definitions):
    file_extension = splitext(path)[1]
    try:
        yield_data_by_id = {
            '.csv': yield_data_by_id_from_csv,
            '.txt': yield_data_by_id_from_txt,
        }[file_extension]
    except KeyError:
        raise CrossComputeConfigurationError(
            f'{file_extension} not supported for batch configuration')
    batch_folder = batch_definition['folder']
    batch_name = batch_definition['name']
    batch_slug = batch_definition['slug']
    batch_definitions = []
    for data_by_id in yield_data_by_id(path, variable_definitions):
        folder = format_text(batch_folder, data_by_id)
        name = format_text(batch_name, data_by_id)
        slug = format_text(
            batch_slug, data_by_id) if batch_slug else format_slug(name)
        batch_definitions.append(batch_definition | {
            'folder': folder, 'name': name, 'slug': slug,
            'uri': BATCH_ROUTE.format(batch_slug=slug),
            'data_by_id': data_by_id})
    return batch_definitions


def get_raw_variable_definitions(configuration, page_type_name):
    page_configuration = configuration.get(page_type_name, {})
    variable_definitions = page_configuration.get('variables', [])
    for variable_definition in variable_definitions:
        variable_definition['type'] = page_type_name
    return variable_definitions


def get_all_variable_definitions(configuration, part_name):
    variable_definitions = get_raw_variable_definitions(
        configuration, part_name).copy()
    for PART_NAME in PART_NAMES[:2]:
        if part_name == PART_NAME:
            continue
        variable_definitions.extend(get_raw_variable_definitions(
            configuration, part_name))
    return variable_definitions


def get_template_texts(configuration, page_type_name):
    template_texts = []
    folder = configuration['folder']
    page_configuration = configuration.get(page_type_name, {})
    for template_definition in page_configuration.get('templates', []):
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
        variable_definitions = get_raw_variable_definitions(
            configuration, page_type_name)
        variable_ids = [_['id'] for _ in variable_definitions if 'id' in _]
        template_texts = [' '.join('{' + _ + '}' for _ in variable_ids)]
    return template_texts


def get_css_uris(configuration):
    style_definitions = configuration.get('display', {}).get('styles', [])
    return [_['uri'] for _ in style_definitions]


def get_display_configuration(configuration):
    folder = configuration['folder']
    display_configuration = configuration.get('display', {})
    has_parent = 'parent' in configuration
    automation_uri = configuration['uri']
    for style_definition in display_configuration.get('styles', []):
        style_uri = style_definition.get('uri', '').strip()
        style_path = style_definition.get('path', '').strip()
        if '//' in style_uri:
            continue
        if not style_uri and not style_path:
            L.error('uri or path required for each style')
            continue
        path = join(folder, style_path)
        if not exists(path):
            L.error('style not found at path %s', path)
            continue
        style_hash = f'{splitext(style_path)[0]}-{time()}.css'
        style_uri = STYLE_ROUTE.format(style_hash=style_hash)
        if has_parent:
            style_uri = automation_uri + style_uri
        style_definition['uri'] = style_uri
    return display_configuration


def get_scalar_text(configuration, key, default=None):
    value = configuration.get(key, default)
    if value is None:
        raise KeyError
    if isinstance(value, dict):
        L.error(
            'quotes should surround text that begins '
            'with a variable id')
        variable_id = list(value.keys())[0]
        value = '{%s}' % variable_id
    return value


def prepare_batch(automation_definition, batch_definition):
    variable_definitions = get_raw_variable_definitions(
        automation_definition, 'input')
    batch_folder = batch_definition['folder']
    variable_definitions_by_path = group_by(variable_definitions, 'path')
    data_by_id = batch_definition.get('data_by_id', {})
    custom_environment = prepare_environment(
        automation_definition,
        variable_definitions_by_path.pop('ENVIRONMENT', []),
        data_by_id)
    if not data_by_id:
        return batch_folder, custom_environment
    automation_folder = automation_definition['folder']
    input_folder = make_folder(join(automation_folder, batch_folder, 'input'))
    for path, variable_definitions in variable_definitions_by_path.items():
        input_path = join(input_folder, path)
        save_variable_data(input_path, variable_definitions, data_by_id)
    return batch_folder, custom_environment


def prepare_environment(
        automation_definition, variable_definitions, data_by_id):
    custom_environment = {}
    data_by_id = data_by_id.copy()
    try:
        for variable_id in (_['id'] for _ in automation_definition.get(
                'environment', {}).get('variables', [])):
            custom_environment[variable_id] = environ[variable_id]
        for variable_id in (_['id'] for _ in variable_definitions):
            if variable_id in data_by_id:
                continue
            data_by_id[variable_id] = environ[variable_id]
    except KeyError:
        raise CrossComputeConfigurationError(
            f'{variable_id} is missing in the environment')
    return custom_environment | get_variable_data_by_id(
        variable_definitions, data_by_id)


def save_variable_data(target_path, variable_definitions, data_by_id):
    file_extension = splitext(target_path)[1]
    variable_data_by_id = get_variable_data_by_id(
        variable_definitions, data_by_id)
    if file_extension == '.dictionary':
        with open(target_path, 'wt') as input_file:
            json.dump(variable_data_by_id, input_file)
    elif len(variable_data_by_id) > 1:
        raise CrossComputeConfigurationError(
            f'{file_extension} does not support multiple variables')
    else:
        variable_data = list(variable_data_by_id.values())[0]
        open(target_path, 'wt').write(variable_data)


def get_variable_data_by_id(variable_definitions, data_by_id):
    variable_data_by_id = {}
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        if None in data_by_id:
            variable_data = data_by_id[None]
        else:
            try:
                variable_data = data_by_id[variable_id]
            except KeyError:
                raise CrossComputeConfigurationError(
                    f'{variable_id} not defined in batch configuration')
        variable_data_by_id[variable_id] = variable_data
    return variable_data_by_id


def format_text(text, data_by_id):
    if not data_by_id:
        return text
    if None in data_by_id:
        f = data_by_id[None]
    else:
        def f(match):
            matching_text = match.group(0)
            expression_text = match.group(1)
            expression_terms = expression_text.split('|')
            variable_id = expression_terms[0].strip()
            try:
                text = data_by_id[variable_id]
            except KeyError:
                L.warning('%s missing in batch configuration', variable_id)
                return matching_text
            try:
                text = apply_functions(
                    text, expression_terms[1:], FUNCTION_BY_NAME)
            except KeyError as e:
                L.error('%s function not supported for string', e)
            return str(text)
    return VARIABLE_ID_PATTERN.sub(f, text)


def yield_data_by_id_from_txt(path, variable_definitions):
    if len(variable_definitions) > 1:
        raise CrossComputeConfigurationError(
            'use .csv to configure multiple variables')

    try:
        variable_id = variable_definitions[0]['id']
    except IndexError:
        variable_id = None

    try:
        with open(path, 'rt') as batch_configuration_file:
            for line in batch_configuration_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                yield parse_data_by_id({
                    variable_id: line}, variable_definitions)
    except OSError:
        raise CrossComputeConfigurationError(f'{path} path not found')


def yield_data_by_id_from_csv(path, variable_definitions):
    try:
        with open(path, 'rt') as file:
            csv_reader = csv.reader(file)
            keys = [_.strip() for _ in next(csv_reader)]
            for values in csv_reader:
                yield parse_data_by_id(dict(zip(
                    keys, values)), variable_definitions)
    except OSError:
        raise CrossComputeConfigurationError(f'{path} path not found')


def parse_data_by_id(data_by_id, variable_definitions):
    for variable_definition in variable_definitions:
        variable_id = variable_definition['id']
        try:
            variable_data = data_by_id[variable_id]
        except KeyError:
            raise CrossComputeDataError({variable_id: 'required'})
        variable_view = VariableView.load_from(variable_definition)
        try:
            variable_data = variable_view.parse(variable_data)
        except CrossComputeDataError as e:
            raise CrossComputeDataError({variable_id: e})
        data_by_id[variable_id] = variable_data
    return data_by_id


class MapMapboxView(VariableView):

    is_asynchronous = True
    view_name = 'map-mapbox'
    css_uris = [
        'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.css',
    ]
    js_uris = [
        'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.js',
    ]

    def render_output(
            self, element_id, variable_data=None,
            variable_configuration=None, request_path=None):
        body_text = (
            f'<div id="{element_id}" '
            f'class="{self.view_name} {self.variable_id}"></div>')
        mapbox_token = get_environment_value('MAPBOX_TOKEN', '')
        js_texts = [
            f"mapboxgl.accessToken = '{mapbox_token}'",
            MAP_MAPBOX_JS_TEMPLATE.substitute({
                'element_id': element_id,
                'data_uri': request_path + '/' + self.variable_path,
                'style_uri': variable_configuration.get(
                    'style', MAP_MAPBOX_CSS_URI),
                'longitude': variable_configuration.get('longitude', 0),
                'latitude': variable_configuration.get('latitude', 0),
                'zoom': variable_configuration.get('zoom', 0),
            }),
        ]
        # TODO: Allow specification of preserveDrawingBuffer
        return {
            'css_uris': self.css_uris,
            'js_uris': self.js_uris,
            'body_text': body_text,
            'js_texts': js_texts,
        }


class MapPyDeckScreenGridView(VariableView):

    is_asynchronous = True
    view_name = 'map-pydeck-screengrid'
    css_uris = [
        'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.css',
    ]
    js_uris = [
        'https://unpkg.com/deck.gl@^8.0.0/dist.min.js',
        'https://api.mapbox.com/mapbox-gl-js/v2.6.0/mapbox-gl.js',
    ]

    def render_output(
            self, element_id, variable_data=None,
            variable_configuration=None, request_path=None):
        body_text = (
            f'<div id="{element_id}" '
            f'class="{self.view_name} {self.variable_id}"></div>')
        mapbox_token = get_environment_value('MAPBOX_TOKEN', '')
        js_texts = [
            MAP_PYDECK_SCREENGRID_JS_TEMPLATE.substitute({
                'data_uri': request_path + '/' + self.variable_path,
                'opacity': variable_configuration.get('opacity', 0.5),
                'element_id': element_id,
                'mapbox_token': mapbox_token,
                'style_uri': variable_configuration.get(
                    'style', MAP_MAPBOX_CSS_URI),
                'longitude': variable_configuration.get('longitude', 0),
                'latitude': variable_configuration.get('latitude', 0),
                'zoom': variable_configuration.get('zoom', 0),
            }),
        ]
        return {
            'css_uris': self.css_uris,
            'js_uris': self.js_uris,
            'body_text': body_text,
            'js_texts': js_texts,
        }


def make_automation_name(automation_index):
    return AUTOMATION_NAME.replace('X', str(automation_index))

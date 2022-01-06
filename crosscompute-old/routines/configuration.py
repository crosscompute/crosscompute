import json
from os import environ
from os.path import join, splitext
from string import Template

from ..macros import get_environment_value


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

import csv
import geojson
import json
from base64 import b64decode, b64encode

from ..exceptions import CrossComputeExecutionError
from ..macros import parse_number
from ..symmetries import cache


def save_json(target_path, value_by_id):
    json.dump(value_by_id, open(target_path, 'wt'))


def save_text(target_path, value):
    open(target_path, 'wt').write(value)


def save_binary(target_path, value):
    open(target_path, 'wb').write(value)


def save_text_json(target_path, value, variable_id, value_by_id_by_path):
    value_by_id_by_path[target_path][variable_id] = value


def save_text_txt(target_path, value, variable_id, value_by_id_by_path):
    open(target_path, 'wt').write(value)


def save_number_json(target_path, value, variable_id, value_by_id_by_path):
    try:
        value = parse_number(value)
    except ValueError:
        raise CrossComputeExecutionError({
            'variable': f'could not parse {variable_id} as a number'})
    value_by_id_by_path[target_path][variable_id] = value


def save_markdown_md(target_path, value, variable_id, value_by_id_by_path):
    open(target_path, 'wt').write(value)


def save_table_csv(target_path, value, variable_id, value_by_id_by_path):
    try:
        columns = value['columns']
        rows = value['rows']
        with open(target_path, 'wt') as target_file:
            csv_writer = csv.writer(target_file)
            csv_writer.writerow(columns)
            csv_writer.writerows(rows)
    except (KeyError, csv.Error):
        raise CrossComputeExecutionError({
            'variable': f'could not parse {variable_id} as a table'})


def save_image_png(target_path, value, variable_id, value_by_id_by_path):
    save_binary(target_path, b64decode(value))


def save_map_geojson(target_path, value, variable_id, value_by_id_by_path):
    geojson.dump(value, target_path)


def load_text(source_path):
    return open(source_path, 'rt').read()


def load_binary(source_path):
    return open(source_path, 'rb').read()


@cache
def load_value_json(source_path, variable_id):
    d = json.load(open(source_path, 'rt'))
    try:
        variable_value = d[variable_id]
    except KeyError:
        raise CrossComputeExecutionError({
            'variable': f'could not find {variable_id} in {source_path}'})
    return variable_value


def load_text_json(source_path, variable_id):
    return load_value_json(source_path, variable_id)


def load_text_txt(source_path, variable_id):
    return load_text(source_path)


def load_number_json(source_path, variable_id):
    value = load_value_json(source_path, variable_id)
    try:
        value = parse_number(value)
    except ValueError:
        raise CrossComputeExecutionError({
            'variable': f'could not parse {variable_id} as a number'})
    return value


def load_markdown_md(source_path, variable_id):
    return load_text(source_path)


def load_table_csv(source_path, variable_id):
    csv_reader = csv.reader(open(source_path, 'rt'))
    columns = next(csv_reader)
    rows = list(csv_reader)
    return {'columns': columns, 'rows': rows}


def load_image_png(source_path, variable_id):
    variable_value = load_binary(source_path)
    variable_value = b64encode(variable_value)
    return variable_value.decode('utf-8')


def load_map_geojson(source_path, variable_id):
    variable_value = geojson.load(open(source_path, 'rt'))
    # TODO: Consider whether to assert FeatureCollection
    return variable_value


SAVE_BY_EXTENSION_BY_VIEW = {
    'text': {
        '.json': save_text_json,
        '.*': save_text_txt,
    },
    'number': {
        '.json': save_number_json,
    },
    'markdown': {
        '.*': save_markdown_md,
    },
    'table': {
        '.csv': save_table_csv,
    },
    'image': {
        '.png': save_image_png,
    },
    'map': {
        '.json': save_map_geojson,
        '.geojson': save_map_geojson,
    },
}


LOAD_BY_EXTENSION_BY_VIEW = {
    'text': {
        '.json': load_text_json,
        '.*': load_text_txt,
    },
    'number': {
        '.json': load_number_json,
    },
    'markdown': {
        '.*': load_markdown_md,
    },
    'table': {
        '.csv': load_table_csv,
    },
    'image': {
        '.png': load_image_png,
    },
    'map': {
        '.json': load_map_geojson,
        '.geojson': load_map_geojson,
    },
}
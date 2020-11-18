import json
from collections import defaultdict
from pytest import raises

from crosscompute.exceptions import (
    CrossComputeExecutionError)
from crosscompute.routines import (
    load_image_png,
    load_map_geojson,
    load_markdown_md,
    load_number_json,
    load_table_csv,
    load_text_json,
    load_text_txt,
    load_value_json,
    render_object,
    save_image_png,
    save_map_geojson,
    save_markdown_md,
    save_number_json,
    save_table_csv,
    save_text_json,
    save_text_txt)


def test_render_object():
    assert render_object({}, as_json=True) == '{}'
    assert render_object({}, as_json=False) == '---\n{}'

    d = {'x': 1}
    assert render_object({
        'a': d,
        'b': d,
    }, as_json=False) == '---\na:\n  x: 1\nb:\n  x: 1'


def test_save_text_json(tmpdir):
    target_path = tmpdir.join('variables.json').strpath
    value = 1
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_text_json(target_path, value, variable_id, value_by_id_by_path)
    assert value_by_id_by_path[target_path][variable_id] == value


def test_save_text_txt(tmpdir):
    target_path = tmpdir.join('book.txt').strpath
    value = 'whee'
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_text_txt(target_path, value, variable_id, value_by_id_by_path)
    assert load_text_txt(target_path, variable_id) == value


def test_save_image_png(tmpdir):
    target_path = tmpdir.join('image.png').strpath
    value = 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVQI12P8//8/AzbAxIADDE4JAFbUAw1h62h+AAAAAElFTkSuQmCC'
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_image_png(target_path, value, variable_id, value_by_id_by_path)
    assert load_image_png(target_path, variable_id) == value


def test_save_number_json(tmpdir):
    target_path = tmpdir.join('variables.json').strpath
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    with raises(CrossComputeExecutionError):
        save_number_json(target_path, 'a', variable_id, value_by_id_by_path)
    save_number_json(target_path, '1', variable_id, value_by_id_by_path)
    assert value_by_id_by_path[target_path][variable_id] == 1


def test_save_markdown_md(tmpdir):
    target_path = tmpdir.join('book.md').strpath
    value = '# whee'
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_markdown_md(target_path, value, variable_id, value_by_id_by_path)
    assert load_markdown_md(target_path, variable_id) == value


def test_save_table_csv(tmpdir):
    target_path = tmpdir.join('table.csv').strpath
    value = {
        'columns': ['x', 'y'],
        'rows': [[1, 2], [2, 3], [3, 4]],
    }
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    with raises(CrossComputeExecutionError):
        save_table_csv(target_path, {}, variable_id, value_by_id_by_path)
    with raises(CrossComputeExecutionError):
        save_table_csv(target_path, {
            'columns': 1, 'rows': 1}, variable_id, value_by_id_by_path)
    save_table_csv(target_path, value, variable_id, value_by_id_by_path)
    assert load_table_csv(target_path, variable_id) == value


def test_save_map_geojson(tmpdir):
    target_path = tmpdir.join('map.geojson').strpath
    value = {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'properties': {
                'population': 200,
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [-112.0372, 46.608058],
            },
        }],
    }
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_map_geojson(target_path, value, variable_id, value_by_id_by_path)
    assert load_map_geojson(target_path, variable_id) == value


def test_load_value_json(tmpdir):
    source_path = tmpdir.join('variables.json').strpath
    variable_id = 'a'
    value = 'A'

    with open(source_path, 'wt') as source_file:
        json.dump({variable_id: value}, source_file)
    with raises(CrossComputeExecutionError):
        load_value_json(source_path, 'x')
    assert load_value_json(source_path, variable_id) == value


def test_load_text_json(tmpdir):
    source_path = tmpdir.join('variables.json').strpath
    variable_id = 'a'
    value = 'A'

    with open(source_path, 'wt') as source_file:
        json.dump({variable_id: value}, source_file)
    assert load_text_json(source_path, variable_id) == value


def test_load_number_json(tmpdir):
    source_path = tmpdir.join('variables.json').strpath
    variable_id = 'a'

    with open(source_path, 'wt') as source_file:
        json.dump({variable_id: 'A'}, source_file)
    with raises(CrossComputeExecutionError):
        load_number_json(source_path, variable_id)

    load_value_json.cache_clear()
    with open(source_path, 'wt') as source_file:
        json.dump({variable_id: '1'}, source_file)
    assert load_number_json(source_path, variable_id) == 1


def test_load_table_csv(tmpdir):
    source_path = tmpdir.join('table.csv').strpath
    value = {
        'columns': ['x', 'y'],
        'rows': [['1', '2'], ['a', 'b']],
    }
    variable_id = 'a'
    value_by_id_by_path = {}
    save_table_csv(source_path, value, variable_id, value_by_id_by_path)
    assert load_table_csv(source_path, variable_id) == {
        'columns': ['x', 'y'],
        'rows': [[1, 2], ['a', 'b']],
    }


def test_load_map_geojson(tmpdir):
    source_path = tmpdir.join('map.geojson').strpath
    variable_id = 'a'

    with open(source_path, 'wt') as source_file:
        source_file.write('')
    with raises(CrossComputeExecutionError):
        load_map_geojson(source_path, variable_id)

    value = {'type': 'FeatureCollection', 'features': []}
    with open(source_path, 'wt') as source_file:
        json.dump(value, source_file)
    assert load_map_geojson(source_path, variable_id) == value

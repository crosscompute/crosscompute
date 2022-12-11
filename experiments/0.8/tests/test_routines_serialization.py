def test_save_image_png(tmpdir):
    target_path = tmpdir.join('image.png').strpath
    value = 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVQI12P8//8/AzbAxIADDE4JAFbUAw1h62h+AAAAAElFTkSuQmCC'
    variable_id = 'a'
    value_by_id_by_path = defaultdict(dict)
    save_image_png(target_path, value, variable_id, value_by_id_by_path)
    assert load_image_png(target_path, variable_id) == value


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

from collections import defaultdict
from pytest import raises

from crosscompute.exceptions import (
    CrossComputeExecutionError)
from crosscompute.routines import (
    load_image_png,
    load_text_txt,
    render_object,
    save_image_png,
    save_number_json,
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

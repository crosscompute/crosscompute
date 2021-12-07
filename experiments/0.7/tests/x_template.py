from crosscompute.scripts.serve import parse_template_parts
from crosscompute.types import DataItem


def test_missing_variable():
    template = '{x}'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [x, y]


def test_missing_variable_with_text():
    template = 'abc {x} xyz'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == ['abc', x, 'xyz', y]


def test_extra_variable():
    template = '{x} {z}'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [x, '{ z }', y]


def test_variable_with_name():
    template = '{x : xyz}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].name == 'xyz'


def test_variable_with_name_and_help():
    template = '{x : xyz ? what is x?}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].name == 'xyz'
    assert parts[0].help == 'what is x?'


def test_variable_with_help():
    template = '{x ? what is x?}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].name == 'x'
    assert parts[0].help == 'what is x?'


def test_variable_name_has_question_mark():
    template = '{x: x?}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].name == 'x?'
    assert parts[0].help == ''

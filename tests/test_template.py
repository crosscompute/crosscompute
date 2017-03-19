from crosscompute.scripts.serve import parse_template_parts
from crosscompute.types import DataItem


def test_missing_variable():
    template = '{x}'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [x, y]


def test_missing_variable_with_markdown():
    text = '+ my script'
    template = '%s {x}' % text
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [text, x, y]


def test_extra_variable():
    template = '{x} {z}'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [x, '{ z }', y]


def test_name():
    template = '{x: xyz}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].name == 'xyz'


def test_help_text():
    template = '{x: xyz ? what is x?}'
    x = DataItem('x', 1)
    parts = parse_template_parts(template, [x])
    assert parts[0].help_text == 'what is x?'

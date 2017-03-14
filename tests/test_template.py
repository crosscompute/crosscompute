from crosscompute.types import DataItem
from crosscompute.scripts.serve import parse_template_parts


def test_unincluded_variable():
    template = '\n{x:name}\n'
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [x, y]


def test_no_title_markdown():
    md = '+ my script'
    template = '%s\n{x:name}\n' % md
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [md, x, y]


def test_other_variable():
    md = '+ my script'
    template = '%s\n{x:name}\n{z}\n' % md
    x, y = DataItem('x', 1), DataItem('y', 2)
    parts = parse_template_parts(template, [x, y])
    assert parts == [md, x, '{ z }', y]

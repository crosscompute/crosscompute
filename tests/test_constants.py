from functools import partial

from crosscompute.constants import (
    VARIABLE_ID_TEMPLATE_PATTERN,
    VARIABLE_ID_WHITELIST_PATTERN)


def test_variable_id_template_pattern():
    f = partial(assert_match, VARIABLE_ID_TEMPLATE_PATTERN)
    f('{a}', 'a')
    f('{ a}', 'a')
    f('{a }', 'a')
    f('{ a }', 'a')
    f('{a}{b}', 'a')


def test_variable_id_whitelist_pattern():
    f = partial(assert_match, VARIABLE_ID_WHITELIST_PATTERN)
    f('{ROOT_URI}', 'ROOT_URI')
    f('{ ROOT_URI}', 'ROOT_URI')
    f('{ROOT_URI }', 'ROOT_URI')
    f('{ ROOT_URI }', 'ROOT_URI')


def assert_match(p, text, variable_id):
    assert p.match(text).group(1) == variable_id

from crosscompute.macros import web
from crosscompute.macros.web import (
    escape_quotes_html,
    escape_quotes_js,
    find_open_port,
    get_html_from_markdown)
from pytest import raises


def test_escape_quotes_html():
    assert escape_quotes_html(1) == 1
    assert escape_quotes_html('"' + "'") == '&#34;&#39;'


def test_escape_quotes_js():
    assert escape_quotes_js(1) == 1
    assert escape_quotes_js('"' + "'") == '\\"' + "\\'"


def test_find_open_port(monkeypatch):
    monkeypatch.setattr(
        web, 'randint', lambda a, b: 5000)
    monkeypatch.setattr(
        web, 'is_port_in_use', lambda x: False)
    assert find_open_port() == 5000
    assert find_open_port(7000) == 7000
    monkeypatch.setattr(
        web, 'is_port_in_use', lambda x: True if x == 7000 else False)
    with raises(OSError):
        find_open_port(7000, 7000, 7000)
    assert find_open_port(7000) == 5000


def test_get_html_from_markdown():
    html = get_html_from_markdown('x')
    assert not html.startswith('<p>') and not html.endswith('</p>')
    html = get_html_from_markdown('x\n\nx')
    assert html.startswith('<p>') and html.endswith('</p>')

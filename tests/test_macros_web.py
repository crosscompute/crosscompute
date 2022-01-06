from crosscompute.macros.web import (
    format_slug,
    get_html_from_markdown)


def test_format_slug():
    assert format_slug('a b,c') == 'a-b-c'


def test_get_html_from_markdown():
    html = get_html_from_markdown('x')
    assert not html.startswith('<p>') and not html.endswith('</p>')
    html = get_html_from_markdown('x\n\nx')
    assert html.startswith('<p>') and html.endswith('</p>')

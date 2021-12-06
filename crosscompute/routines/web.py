from markdown import markdown


def get_html_from_markdown(text):
    html = markdown(text)
    if '</p>\n<p>' not in html:
        html = html.removeprefix('<p>')
        html = html.removesuffix('</p>')
    return html

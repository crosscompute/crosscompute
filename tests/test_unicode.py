# coding: utf-8
from conftest import TOOL_FOLDER
from crosscompute.tests import run
from test_serve import serve


def test_print_unicode():
    standard_output = run(TOOL_FOLDER, 'print-unicode')[0]
    assert 'standard_outputs.a = клубника' in standard_output
    assert 'standard_errors.b = малина' in standard_output


def test_unicode_content_run():
    standard_output = run(TOOL_FOLDER, 'arabic_content', dict(
                             arabic_text_path='static/arabic_content.txt'))[0]
    assert 'للل' in standard_output


def test_unicode_content_serve():
    soup = serve('arabic_content', dict(
                 arabic_text_path='static/arabic_content.txt'))
    assert 'للل' in soup.find(id='standard_output_').text.strip()


def test_unicode_name_run():
    # this passes for some reason 'arabic-name'
    stdout = run(TOOL_FOLDER, 'arabic_name',
                 dict(arabic_text_path='static/ل.txt'))
    print(stdout)
    assert 'number of words: 2' in stdout[0]


def test_unicode_name_serve():
    soup = serve('arabic_name', dict(arabic_text_path='static/ل.txt'))
    assert ('number of words: 2' in soup.find(id='standard_output_')
                                        .text.strip())

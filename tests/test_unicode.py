# coding: utf-8
from crosscompute.tests import run

import test_string


def test_stream_logging():
    x = '고기'.decode('utf-8')
    test_string.test_stream_logging(x)


def test_stream_parsing():
    x = 'клубника'.decode('utf-8')
    test_string.test_stream_parsing(x)


def test_file_name():
    args = 'file-name',
    r = run(*args)
    assert r['standard_output'] == 'acta non verba'


def test_file_content(tmpdir):
    test_string.test_file_content(tmpdir, 'assets/unicode.txt')

# coding: utf-8
from crosscompute.tests import run

import test_string


def test_stream_logging(tmpdir):
    x = '고기'.decode('utf-8')
    test_string.test_stream_logging(tmpdir, x)


def test_stream_parsing(tmpdir):
    x = 'клубника'.decode('utf-8')
    test_string.test_stream_parsing(tmpdir, x)


def test_file_name_with_unicode(tmpdir):
    args = str(tmpdir), 'file-name-with-unicode',
    r = run(*args)
    assert r['standard_output'] == 'acta non verba'


def test_file_content(tmpdir):
    test_string.test_file_content(tmpdir, 'assets/unicode.txt')

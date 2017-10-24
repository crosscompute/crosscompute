# coding: utf-8
from crosscompute.tests import run

import test_string


def test_output_logging(tmpdir):
    x = u'고기'
    test_string.test_output_logging(tmpdir, x)


def test_output_parsing(tmpdir):
    x = u'клубника'
    test_string.test_output_parsing(tmpdir, x)


def test_file_name_with_unicode(tmpdir):
    args = str(tmpdir), 'file-name-with-unicode',
    r = run(*args)
    assert r['raw_output'] == 'acta non verba'


def test_file_content(tmpdir):
    test_string.test_file_content(tmpdir, 'assets/unicode.txt')

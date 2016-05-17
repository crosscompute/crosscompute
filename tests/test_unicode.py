# coding: utf-8
from crosscompute.tests import run

import test_string
from conftest import TOOL_FOLDER


def test_standard_output():
    x = '야채'.decode('utf-8')
    test_string.test_standard_output(x)


def test_standard_error():
    x = '고기'.decode('utf-8')
    test_string.test_standard_error(x)


def test_standard_outputs():
    x = 'клубника'.decode('utf-8')
    test_string.test_standard_outputs(x)


def test_standard_errors():
    x = 'малина'.decode('utf-8')
    test_string.test_standard_errors(x)


def test_file_name_with_unicode():
    args = TOOL_FOLDER, 'file-name-with-unicode'
    r = run(*args)
    assert r['standard_output'] == 'abc'


def test_file_content(tmpdir):
    test_string.test_file_content(tmpdir, 'assets/unicode.txt')

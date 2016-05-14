# coding: utf-8
from conftest import TOOL_FOLDER
from crosscompute.tests import run
from string import digits, letters


def test_capture_standard_output():
    standard_output = run(TOOL_FOLDER, 'count-characters', {
        'phrase': letters + digits})[0]
    assert '62' in standard_output


def test_accept_script_filename_with_spaces():
    standard_output = run(
        TOOL_FOLDER, 'accept-script-filename-with-spaces-in-single-quotes')[0]
    assert 'abc = xyz' in standard_output
    standard_output = run(
        TOOL_FOLDER, 'accept-script-filename-with-spaces-in-double-quotes')[0]
    assert 'abc = xyz' in standard_output

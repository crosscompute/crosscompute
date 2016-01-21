from conftest import TOOL_FOLDER
from crosscompute.tests import run
from string import digits, letters


def test_run():
    standard_output = run(TOOL_FOLDER, '', {
        'phrase': letters + digits})[0]
    assert '62' in standard_output


if __name__ == '__main__':
    from sys import argv
    phrase = argv[1]
    print(len(phrase))

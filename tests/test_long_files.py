import re
from conftest import TOOL_FOLDER
from crosscompute.tests import run
from test_serve import serve


def test_long_output():
    standard_output = run(TOOL_FOLDER, 'long_output')[0]
    assert 10000 == (len(re.findall("I love python", standard_output))/2)


def test_long_file():
    soup = serve('long_file', dict(file_text_path='static/long_file.txt'))
    assert 20000 == len(re.findall('I love python',
                        soup.find(id='standard_output_').text))


def test_many_points():
    soup = serve('many_points', dict(
                 file_table_path='static/worldcities.csv'))
    # test to see if number of points matches
    assert 6000 == len(soup.find(id="my_geotable__").findAll('tbody'))

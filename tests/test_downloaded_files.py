import re
from os import path

from conftest import TOOL_FOLDER
from crosscompute.tests import run


def test_download():
    stdout = run(TOOL_FOLDER, "many_points",
                 dict(file_table_path="static/worldcities.csv"))
    match = re.search(
            '(standard_outputs.my_geotable_path = )(.+)\n', stdout[0])
    assert path.exists(match.group(2))

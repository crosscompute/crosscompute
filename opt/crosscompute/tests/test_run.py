import shlex
import subprocess
from invisibleroads_macros.disk import cd
from os.path import exists
from pytest import mark

from conftest import ADD_INTEGERS_FOLDER, EXAMPLES_FOLDER, SUBMODULES_REQUIRED


@mark.skipif(not exists(ADD_INTEGERS_FOLDER), reason=SUBMODULES_REQUIRED)
def test_run():
    terms = shlex.split(
        'crosscompute run add-integers --x_integer 2 --y_integer 3')
    with cd(EXAMPLES_FOLDER):
        process = subprocess.Popen(
            terms, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    assert 'standard_output = 5' in stdout

from pytest import raises

from crosscompute.exceptions import CrossComputeExecutionError
from crosscompute.routines.automation import _run_command


def test_run_command(tmp_path):
    o_path = tmp_path / 'o.txt'
    e_path = tmp_path / 'e.txt'
    with raises(CrossComputeExecutionError):
        _run_command('', tmp_path, {}, o_path, e_path)
    with raises(CrossComputeExecutionError):
        _run_command('python x', tmp_path, {}, o_path, e_path)
    _run_command('python --help', tmp_path, {}, o_path, e_path)

from pytest import raises

from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeExecutionError)
from crosscompute.routines.automation import _run_command


def test_run_command(tmp_path):
    o_path = tmp_path / 'o.txt'
    e_path = tmp_path / 'e.txt'
    with open(o_path, 'wt') as o_file, open(e_path, 'w+t') as e_file:
        with raises(CrossComputeConfigurationError):
            _run_command('', tmp_path, {}, o_file, e_file)
        with raises(CrossComputeExecutionError):
            _run_command('python x', tmp_path, {}, o_file, e_file)
        _run_command('python --help', tmp_path, {}, o_file, e_file)

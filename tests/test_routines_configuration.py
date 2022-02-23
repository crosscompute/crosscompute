from pytest import raises

from crosscompute import __version__
from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from crosscompute.routines.configuration import (
    validate_automation_identifiers,
    validate_protocol)


class DummyConfiguration(dict):
    index = 0


def test_validate_protocol():
    with raises(CrossComputeError):
        validate_protocol({})
    with raises(CrossComputeConfigurationError):
        validate_protocol({'crosscompute': ''})
    with raises(CrossComputeConfigurationError):
        validate_protocol({'crosscompute': 'x'})
    validate_protocol({'crosscompute': __version__})


def test_validate_automation_identifiers():
    d = validate_automation_identifiers(DummyConfiguration({}))
    assert d['name'] == 'Automation 0'
    assert d['version'] == '0.0.0'
    assert d['slug'] == 'automation-0'
    assert d['uri'] == '/a/automation-0'
    d = validate_automation_identifiers(DummyConfiguration({
        'name': 'x', 'version': 'x', 'slug': 'x'}))
    assert d['name'] == 'x'
    assert d['version'] == 'x'
    assert d['slug'] == 'x'
    assert d['uri'] == '/a/x'

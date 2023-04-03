from pytest import raises

from crosscompute import __version__
from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from crosscompute.routines.configuration import (
    process_header_footer_options,
    process_page_number_options,
    validate_automation_identifiers,
    validate_protocol,
    validate_templates,
    validate_variables)


class DummyConfiguration(dict):
    index = 0


def test_validate_protocol():
    with raises(CrossComputeError):
        validate_protocol({})
    with raises(CrossComputeConfigurationError):
        validate_protocol({'crosscompute': ''})
    with raises(CrossComputeConfigurationError):
        validate_protocol({'crosscompute': '0.0.0'})
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


def test_validate_variables():
    d = validate_variables(DummyConfiguration({}))
    assert len(d['variable_definitions_by_step_name']['input']) == 0
    with raises(CrossComputeConfigurationError):
        validate_variables(DummyConfiguration({
            'input': {'variables': [{
                'id': 'x',
                'view': 'string',
                'path': 'x.txt',
            }, {
                'id': 'x',
                'view': 'string',
                'path': 'x.txt',
            }]}}))
    d = validate_variables(DummyConfiguration({
        'input': {'variables': [{
            'id': 'x',
            'view': 'string',
            'path': 'x.txt',
        }, {
            'id': 'y',
            'view': 'string',
            'path': 'y.txt',
        }]}}))
    assert len(d['variable_definitions_by_step_name']['input']) == 2


def test_validate_templates(tmp_path):
    c = DummyConfiguration({'input': {'templates': []}})
    c.folder = tmp_path

    d = validate_templates(c)
    assert len(d['template_definitions_by_step_name']['input']) == 0

    c['input']['templates'] = [{}]
    with raises(CrossComputeConfigurationError):
        d = validate_templates(c)

    c['input']['templates'] = [{'path': 'x.md'}]
    with raises(CrossComputeConfigurationError):
        d = validate_templates(c)

    tmp_path.joinpath('x.md').open('wt').write('')
    c['input']['templates'] = [{'path': 'x.md'}, {'path': 'x.md'}]
    with raises(CrossComputeConfigurationError):
        d = validate_templates(c)

    c['input']['templates'] = [{'path': 'x.md'}]
    d = validate_templates(c)
    assert len(d['template_definitions_by_step_name']['input']) == 1


def test_process_header_footer_options():
    d = {'header-footer': {}}
    process_header_footer_options('x', d)
    assert not d.get('header-footer').get('skip-first')
    d = {'header-footer': {'skip-first': 'true'}}
    process_header_footer_options('x', d)
    assert d['header-footer'].get('skip-first')


def test_process_page_number_options():
    d = {}
    process_page_number_options('x', d)

    d = {'page-number': {'location': 'x'}}
    with raises(CrossComputeConfigurationError):
        process_page_number_options('x', d)

    d = {'page-number': {'alignment': 'x'}}
    with raises(CrossComputeConfigurationError):
        process_page_number_options('x', d)

    d = {'page-number': {
        'location': 'footer', 'alignment': 'right'}}
    process_page_number_options('x', d)

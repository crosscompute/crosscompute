def test_normalize_data_dictionary():
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary([], 'text')
    with raises(CrossComputeDefinitionError):
        normalize_data_dictionary({}, 'text')
    assert normalize_data_dictionary({
        'value': '1'}, 'number') == {'value': 1}
    assert normalize_data_dictionary({
        'dataset': {'id': 'x', 'version': {'id': 'a'}},
    }, 'number')['dataset']['id'] == 'x'
    assert normalize_data_dictionary({
        'file': {'id': 'x'},
    }, 'number')['file']['id'] == 'x'


def test_normalize_file_dictionary():
    with raises(CrossComputeDefinitionError):
        normalize_file_dictionary('')
    with raises(CrossComputeDefinitionError):
        normalize_file_dictionary({})
    assert normalize_file_dictionary({'id': 'a'})['id'] == 'a'

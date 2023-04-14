def normalize_test_dictionaries(raw_test_dictionaries):
    check_list(raw_test_dictionaries, 'tests')
    if not raw_test_dictionaries:
        raise CrossComputeDefinitionError({
            'tests': 'must have at least one test defined'})
    try:
        test_dictionaries = [{
            'folder': _['folder'],
        } for _ in raw_test_dictionaries]
    except TypeError:
        raise CrossComputeDefinitionError({
            'tests': 'must be a list of dictionaries'})
    except KeyError as e:
        raise CrossComputeDefinitionError({
            e.args[0]: 'is required for each test'})
    return test_dictionaries


def normalize_environment_dictionary(raw_environment_dictionary):
    d = {}
    try:
        d.update({
            'image': raw_environment_dictionary['image'],
            'processor': raw_environment_dictionary['processor'],
            'memory': raw_environment_dictionary['memory'],
        })
    except KeyError as e:
        raise CrossComputeDefinitionError({
            'environment': 'requires ' + e.args[0]})
    if 'variables' in raw_environment_dictionary:
        d['variables'] = normalize_environment_variable_dictionaries(
            raw_environment_dictionary['variables'])
    return d

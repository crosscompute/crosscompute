def test_find_relevant_path():
    path = RESULT_DEFINITION_PATH
    name = basename(path)
    stem_path, good_extension = splitext(path)
    bad_extension = '.css'

    with raises(OSError):
        find_relevant_path(
            join(EXAMPLES_FOLDER, 'x' + good_extension),
            'x' + good_extension)

    assert find_relevant_path(
        path,
        'x' + good_extension,
    ) == path

    assert find_relevant_path(
        stem_path + bad_extension,
        'x' + good_extension,
    ) == path

    assert find_relevant_path(
        EXAMPLES_FOLDER,
        name,
    ) == path

    assert find_relevant_path(
        join(EXAMPLES_FOLDER, 'templates', 'output', 'standard.md'),
        name,
    ) == path

    with raises(OSError):
        find_relevant_path('/', name)

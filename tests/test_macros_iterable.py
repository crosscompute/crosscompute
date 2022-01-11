from crosscompute.macros.iterable import extend_uniquely


def test_extend_uniquely():
    items = [1, 2, 3, 4, 5]
    new_items = [1, 2, 33, 44, 52]
    extend_uniquely(items, new_items)
    assert len(items) == 8

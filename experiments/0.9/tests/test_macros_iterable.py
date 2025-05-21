from crosscompute.macros.iterable import extend_uniquely


def test_extend_uniquely():
    items = [1, 2]
    extend_uniquely(items, [2, 3])
    assert len(items) == 3

from math import nan

from crosscompute.macros import sanitize_json_value


def test_sanitize_json_value():
    assert sanitize_json_value(nan) is None
    assert nan not in sanitize_json_value([[nan, 1, 'a', None]])[0]
    assert nan not in sanitize_json_value({nan: nan}).keys()
    assert nan not in sanitize_json_value({nan: nan}).values()

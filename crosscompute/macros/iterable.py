import operator
from collections import OrderedDict, defaultdict


class LRUDict(OrderedDict):
    # https://gist.github.com/davesteele/44793cd0348f59f8fadd49d7799bd306

    def __init__(self, *args, maximum_length: int, **kwargs):
        assert maximum_length > 0
        self.maximum_length = maximum_length
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().move_to_end(key)
        while len(self) > self.maximum_length:
            super().__delitem__(next(iter(self)))

    def __getitem__(self, key):
        value = super().__getitem__(key)
        super().move_to_end(key)
        return value


def group_by(items, key):
    items_by_key = defaultdict(list)
    for item in items:
        items_by_key[item[key]].append(item)
    return dict(items_by_key)


def find_item(
        items, key, value, get_value=lambda item, key: getattr(item, key),
        normalize=lambda _: _, compare=operator.eq):
    normalized_value = normalize(value)

    def is_match(item):
        try:
            v = get_value(item, key)
        except KeyError:
            is_match = False
        else:
            normalized_v = normalize(v)
            is_match = compare(normalized_value, normalized_v)
        return is_match

    return next(filter(is_match, items))


def extend_uniquely(old_items, new_items):
    old_items.extend(_ for _ in new_items if _ not in old_items)

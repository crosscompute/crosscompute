import operator
from collections import defaultdict


def group_by(items, key):
    items_by_key = defaultdict(list)
    for item in items:
        items_by_key[item[key]].append(item)
    return dict(items_by_key)


def find_item(items, key, value, normalize=lambda _: _, compare=operator.eq):
    normalized_value = normalize(value)

    def is_match(item):
        try:
            v = item.get(key)
        except KeyError:
            is_match = False
        else:
            normalized_v = normalize(v)
            is_match = compare(normalized_value, normalized_v)
        return is_match

    return next(filter(is_match, items))


def extend_uniquely(old_items, new_items):
    old_items.extend(_ for _ in new_items if _ not in old_items)

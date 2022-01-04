from collections import defaultdict


def group_by(items, key):
    items_by_key = defaultdict(list)
    for item in items:
        items_by_key[item[key]].append(item)
    return dict(items_by_key)

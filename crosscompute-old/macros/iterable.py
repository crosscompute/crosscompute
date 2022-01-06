def append_uniquely(items, item):
    if item not in items:
        items.append(item)


def extend_uniquely(old_items, new_items):
    old_items.extend(_ for _ in new_items if _ not in old_items)



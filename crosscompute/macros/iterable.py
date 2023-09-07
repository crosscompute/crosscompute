def extend_uniquely(old_items, new_items):
    old_items.extend(_ for _ in new_items if _ not in old_items)

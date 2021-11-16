import operator


def append_once(item, items):
    if item not in items:
        items.append(item)


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

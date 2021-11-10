import operator


def find_item(items, key, value, normalize=lambda _: _, compare=operator.eq):
    normalized_value = normalize(value)

    def is_match(v):
        normalized_v = normalize(v)
        return compare(normalized_value, normalized_v)

    return next(filter(lambda _: is_match(_[key]), items))

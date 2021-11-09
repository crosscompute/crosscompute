def find_dictionary(dictionaries, key, value, method_name='__eq__'):
    # TODO: Consider whether to let user specify compare
    normalized_value = value.casefold()
    compare = getattr(normalized_value, method_name)

    def is_match(v):
        normalized_v = v.casefold()
        return compare(normalized_v)

    return next(filter(lambda _: is_match(_[key]), dictionaries))

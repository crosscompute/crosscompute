def find_dictionary(dictionaries, key, value):

    def is_match(v):
        return v.casefold() == value.casefold()

    return next(filter(lambda _: is_match(_[key]), dictionaries))

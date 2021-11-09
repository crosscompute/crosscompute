from .text import normalize_key


def get_slug_from_name(name):
    return normalize_key(name, word_separator='-')

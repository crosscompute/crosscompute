from .text import normalize_key


def format_slug(text):
    return normalize_key(text, word_separator='-')

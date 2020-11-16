try:
    from functools import cache
except ImportError:
    from functools import lru_cache

    def cache(f):
        return lru_cache(maxsize=None)(f)


import shlex
try:
    join_command_terms = shlex.join
except AttributeError:

    def join_command_terms(terms):
        return ' '.join(shlex.quote(_) for _ in terms)

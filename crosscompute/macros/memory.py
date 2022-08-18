class CachedProperty():
    '''
    Property computes once per instance. Delete the property to reset.
    See https://github.com/bottlepy/bottle/commit/fa7733e075.
    '''

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, Class):
        if obj is None:
            return self
        value = obj.__dict__[self.f.__name__] = self.f(obj)
        return value

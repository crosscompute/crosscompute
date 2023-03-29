from time import time


class Clock:

    def __init__(self):
        self.time_by_key = {}

    def start(self, name):
        self.time_by_key[name + '<'] = time()
        self.time_by_key['>' + name] = None

    def end(self, name):
        self.time_by_key['>' + name] = time()

    def is_in(self, name):
        d = self.time_by_key
        time_a = d.get(name + '<')
        time_z = d.get('>' + name)
        if not time_a:
            return False
        if not time_z:
            return True
        return False

    def get_time(self, name):
        return self.time_by_key.get('>' + name, 0)

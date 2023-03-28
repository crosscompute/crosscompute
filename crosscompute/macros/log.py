from datetime import datetime


class Clock:

    def __init__(self, get_now=datetime.now):
        self.get_now = get_now
        self.datetimes = {}

    def start(self, name):
        self.datetimes[name + '<'] = self.get_now()

    def end(self, name):
        self.datetimes['>' + name] = self.get_now()

    def in(self, name):
        d = self.datetimes
        datetime_a = d.get(name + '<')
        datetime_z = d.get('>' + name)
        if not datetime_a:
            return False
        if not datetime_z:
            return True
        return False

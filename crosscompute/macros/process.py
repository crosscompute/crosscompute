from logging import getLogger
from multiprocessing import Process


class LoggableProcess(Process):

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        L.debug(
            'started %s%s process %s', self.name,
            ' daemon' if self.daemon else '', self.ident)


class StoppableProcess(LoggableProcess):

    def stop(
            self,
            sigterm_timeout_in_seconds=3,
            sigkill_timeout_in_seconds=1):
        '''
        Stop the process using SIGTERM and, if necessary, SIGKILL.
        See watchgod/main.py for original code.
        '''
        L.debug('terminating %s process %s', self.name, self.ident)
        self.terminate()
        self.join(sigterm_timeout_in_seconds)
        if self.exitcode is None:
            L.debug('killing %s process %s', self.name, self.ident)
            self.kill()
            self.join(sigkill_timeout_in_seconds)


L = getLogger(__name__)

from logging import getLogger
from multiprocessing import Process


class StoppableProcess(Process):

    def stop(
            self,
            sigterm_timeout_in_seconds=3,
            sigkill_timeout_in_seconds=1):
        '''
        Stop the process using SIGTERM and, if necessary, SIGKILL.
        See watchgod/main.py for original code.
        '''
        L.debug('sending sigterm to process %s', self.ident)
        self.terminate()
        self.join(sigterm_timeout_in_seconds)
        if self.exitcode is None:
            L.debug('sending sigkill to process %s', self.ident)
            self.kill()
            self.join(sigkill_timeout_in_seconds)


L = getLogger(__name__)

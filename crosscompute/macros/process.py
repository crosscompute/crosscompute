import logging
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
        logging.debug('sending sigterm to process %s', self.ident)
        self.terminate()
        self.join(sigterm_timeout_in_seconds)
        if self.exitcode is None:
            logging.debug('ending sigkill to process %s', self.ident)
            self.kill()
            self.join(sigkill_timeout_in_seconds)

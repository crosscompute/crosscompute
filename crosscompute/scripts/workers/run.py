import shlex

from .. import OutputtingScript, run_safely
from ...routines import run_worker


class RunWorkerScript(OutputtingScript):

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        run_safely(run_worker, [
            shlex.join(argv),
        ], is_quiet, as_json)

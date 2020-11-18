from .. import OutputtingScript, run_safely
from ...routines import run_worker
from ...symmetries import join_command_terms


class RunWorkerScript(OutputtingScript):

    def run(self, args, argv):
        super().run(args, argv)
        is_quiet = args.is_quiet
        as_json = args.as_json

        run_safely(run_worker, [
            join_command_terms(argv),
        ], is_quiet, as_json)

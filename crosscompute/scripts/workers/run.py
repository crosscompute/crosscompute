from .. import OutputtingScript
from ...routines import (
    get_server_url,
    get_token,
    run_safely,
    run_worker)


class RunWorkerScript(OutputtingScript):

    def run(self, args, argv):
        super().run(args, argv)
        command_terms = argv
        run_safely(run_worker, [
            get_server_url(),
            get_token(),
            command_terms,
        ], args.as_json, args.is_quiet)

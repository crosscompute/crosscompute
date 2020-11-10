from .. import OutputtingScript
from ...routines import (
    get_server_url,
    get_token,
    run_safely,
    run_worker)


class RunWorkerScript(OutputtingScript):

    def run(self, args, argv):
        super().run(args, argv)
        as_json = args.as_json
        is_quiet = args.is_quiet
        run_safely(run_worker, [
            get_server_url(),
            get_token(),
            as_json,
            is_quiet,
        ], as_json, is_quiet)

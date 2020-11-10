from .. import OutputtingScript
from ...routines import (
    add_project,
    load_definition,
    render_object,
    run_safely)


class AddProjectScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'project_definition_path',
            metavar='PROJECT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        as_json = args.as_json
        is_quiet = args.is_quiet

        project_dictionary = load_definition(
            args.project_definition_path, kinds=['project'])

        if args.is_mock:
            if not is_quiet:
                print(render_object(project_dictionary, as_json))
            return
        d = run_safely(add_project, [
            project_dictionary,
        ], as_json, is_quiet)

        if is_quiet:
            return
        print(render_object(d, as_json))

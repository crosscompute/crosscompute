import yaml

from .. import OutputtingScript
from ...exceptions import CrossComputeError
from ...routines import (
    fetch_resource,
    get_project_summary,
    load_definition,
    render_object,
    run_safely)


class SetProjectScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'project_definition_path',
            metavar='PROJECT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        project_definition_path = args.project_definition_path
        as_json = args.as_json
        is_quiet = args.is_quiet

        try:
            project_dictionary = load_definition(
                project_definition_path, kinds=['project'])
        except CrossComputeError as e:
            if is_quiet:
                exit(1)
            exit(render_object(e.args[0], as_json))

        if args.is_mock:
            if not is_quiet:
                print(render_object(project_dictionary, as_json))
            return
        project_id = project_dictionary.get('id')
        d = run_safely(fetch_resource, [
            'projects', project_id,
            'PATCH' if project_id else 'POST',
            project_dictionary,
        ], as_json, is_quiet)

        project_summary = get_project_summary(d)
        open(project_definition_path, 'wt').write('\n'.join([
            '---',
            yaml.dump(project_summary).strip()]))

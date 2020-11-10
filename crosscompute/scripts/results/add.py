from .. import OutputtingScript
from ...routines import (
    add_result,
    load_definition,
    render_object,
    run_safely)


class AddResultScript(OutputtingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument(
            '--name', metavar='RESULT_NAME',
            dest='result_name')
        argument_subparser.add_argument(
            '--toolId', metavar='TOOL_ID',
            dest='tool_id')
        argument_subparser.add_argument(
            '--toolVersionId', metavar='TOOL_VERSION_ID',
            dest='tool_version_id')
        argument_subparser.add_argument(
            '--projectId', metavar='PROJECT_ID',
            dest='project_id')
        argument_subparser.add_argument(
            '--mock', action='store_true', dest='is_mock')
        argument_subparser.add_argument(
            'result_definition_path',
            metavar='RESULT_DEFINITION_PATH')

    def run(self, args, argv):
        super().run(args, argv)
        result_name = args.result_name
        tool_id = args.tool_id
        tool_version_id = args.tool_version_id
        project_id = args.project_id
        as_json = args.as_json
        result_dictionary = load_definition(
            args.result_definition_path, kinds=['result'])
        if result_name:
            result_dictionary['name'] = result_name
        if tool_id:
            tool_dictionary = result_dictionary.get('tool', {})
            tool_dictionary['id'] = tool_id
            result_dictionary['tool'] = tool_dictionary
        if tool_version_id:
            tool_dictionary = result_dictionary.get('tool', {})
            tool_version = tool_dictionary.get('version', {})
            tool_version['id'] = tool_version_id
            tool_dictionary['version'] = tool_version
            result_dictionary['tool'] = tool_dictionary
        if project_id:
            project_dictionary = result_dictionary.get('project', {})
            project_dictionary['id'] = project_id
        if args.is_mock:
            print(render_object(result_dictionary, as_json))
            return
        d = run_safely(add_result, [
            result_dictionary,
        ], as_json, args.is_quiet)
        print(render_object(d, as_json))

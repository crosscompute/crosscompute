from invisibleroads_macros.disk import cd
from subprocess import Popen, PIPE


def run(tool_folder, tool_name, result_arguments=None):
    command_terms = ['crosscompute', 'run', tool_name]
    for k, v in (result_arguments or {}).items():
        command_terms.extend(['--%s' % k, str(v)])
    with cd(tool_folder):
        process = Popen(command_terms, stdout=PIPE, stderr=PIPE)
    standard_output, standard_error = process.communicate()
    print(standard_output)
    print(standard_error)
    return standard_output, standard_error

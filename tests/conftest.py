from collections.abc import ByteString, Sequence
from os.path import dirname, join


TESTS_FOLDER = dirname(__file__)
EXAMPLES_FOLDER = join(TESTS_FOLDER, 'examples')
TOOL_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'tool.yml')
TOOL_MINIMAL_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'tool-minimal.yml')
RESULT_DEFINITION_PATH = join(EXAMPLES_FOLDER, 'result.yml')


def flatten_values(d):
    values = []
    vs = [d]
    for v in vs:
        if hasattr(v, 'items'):
            vs.extend(v.values())
        elif isinstance(v, Sequence) and not isinstance(v, (str, ByteString)):
            vs.extend(v)
        values.append(v)
    return values

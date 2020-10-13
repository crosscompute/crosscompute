from crosscompute.routines import load_tool_definition

from conftest import flatten_values, TOOL_MINIMAL_DEFINITION_PATH


def test_load_tool_definition():
    tool_definition = load_tool_definition(TOOL_MINIMAL_DEFINITION_PATH)
    for value in flatten_values(tool_definition):
        assert type(value) in [dict, list, int, str]
    assert len(tool_definition['input']['variables']) == 2

from crosscompute.routines import load_tool_definition

from conftest import TOOL_MINIMAL_DEFINITION_PATH


def test_load_tool_definition():
    tool_definition = load_tool_definition(TOOL_MINIMAL_DEFINITION_PATH)
    assert len(tool_definition['input']['variables']) == 2

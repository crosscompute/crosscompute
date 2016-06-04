from crosscompute import configurations


def test_get_tool_definition_by_name_from_path():
    tool_template = "[crosscompute tool]"
    command_template = "command_template = python run.py"
    c = "dummy/cc.ini"
    d = "dummy"
    with open(c, 'w') as f:
        f.write(tool_template + "\n")
        f.write(command_template)
    res = configurations.get_tool_definition_by_name_from_path(
            c, d)
    assert 'tool' in res.keys()
    x = res['tool']
    assert x['command_template'] == 'python run.py'
    assert x['tool_name'] == 'tool'
    assert not x['argument_names']

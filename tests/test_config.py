from crosscompute import configurations
from os.path import join


FOLDER = "./dummy/"
FILE = join(FOLDER, "cc.ini")


def test_get_tool_definition_by_name_from_path():
    tool_template = "[crosscompute tool]"
    command_template = "command_template = python run.py"
    with open(FILE, 'w') as f:
        f.write(tool_template + "\n")
        f.write(command_template)
    res = configurations.get_tool_definition_by_name_from_path(
            FILE, FOLDER)
    assert 'tool' in res.keys()
    x = res['tool']
    assert x['command_template'] == 'python run.py'
    assert x['tool_name'] == 'tool'
    assert not x['argument_names']
    print(configurations.format_available_tools(res))


def test_default_tool():
    """multiple tools of the same name, last one is default goto tool"""
    with open(FILE, 'w') as f:
        f.write(
          "[crosscompute]\ncommand_template=python run.py\n\t{x}\n\t{y}\n")
        f.write(
          "[crosscompute]\ncommand_template=python run.py\n\t{x}\n")
        f.write(
          "[crosscompute t]\ncommand_template=python run.py\n\t{x}\n")
    tools = (
        configurations.get_tool_definition_by_name_from_path(FILE, FOLDER))
    assert len(tools['tests/dummy/']['argument_names']) == 1
    assert len(tools) == 2
    assert "2 available" in configurations.format_available_tools(tools)


def test_argument_parser():
    assert len(configurations.parse_tool_argument_names(
                "python run.py {var1} {var3}\n\t{var2} {var4}")) == 4
    assert len(configurations.parse_tool_argument_names(
                "python run.py {var1} {var3}\n")) == 2
    assert len(configurations.parse_tool_argument_names(
                "python run.py {var1}")) == 1
    assert len(configurations.parse_tool_argument_names(
                "python run.py (x)")) == 0
    assert ("x", "y") == configurations.parse_tool_argument_names(
                "python run.py {x} {y}")

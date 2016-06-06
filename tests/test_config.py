from crosscompute import configurations
from os.path import join


FOLDER = "./dummy/"
FILE = join(FOLDER, "dummy.ini")
TEMPLATE = "[crosscompute {n}]\ncommand_template = python run.py {a}\n{d}\n"


def test_get_tool_definition_by_name_from_path():
    with open(FILE, 'w') as f:
        f.write(TEMPLATE.format(n="tool", a="", d=""))
    res = configurations.get_tool_definition_by_name_from_path(
            FILE, FOLDER)
    assert 'tool' in res
    x = res['tool']
    assert x['command_template'].strip() == 'python run.py'
    assert x['tool_name'].strip() == 'tool'
    assert not x['argument_names']


def test_default_tool():
    """multiple tools of the same name, last one is default goto tool"""
    with open(FILE, 'w') as f:
        f.write(TEMPLATE.format(a="\n\t".join(["{x}", "{y}"]), d="", n=""))
        f.write(TEMPLATE.format(a="\n\t".join(["{x}"]), d="", n=""))
        f.write(TEMPLATE.format(a="\n\t".join(["{x}"]), d="", n="t"))
    tools = (
        configurations.get_tool_definition_by_name_from_path(FILE, FOLDER))
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


def test_get_tool_definition_by_name_from_folder():
    """multiple tools of the same name, last one is default goto tool"""
    with open(FILE, 'w') as f:
        f.write(TEMPLATE.format(d="",
                n="", a="\n\t".join(["{x}", "{y}"])))
        f.write(TEMPLATE.format(d="",
                n="", a="\n\t".join(["{x}", "{y}", "{z}"])))
        f.write(TEMPLATE.format(d="",
                n="t", a="\n\t".join(["{x}"])))
    tools = configurations.get_tool_definition_by_name_from_folder(FOLDER)
    assert len(tools) == 2
    assert 't' in tools


def test_get_tool_def():
    """multiple tools of the same name, last one is default goto tool"""
    TEMPLATE = "[crosscompute {n}]\ncommand_template = python run.py {args}\n"
    with open(FILE, 'w') as f:
        f.write(TEMPLATE.format(d="",
                n="", args="\n\t".join(["{x}", "{y}"])))
        f.write(TEMPLATE.format(d="",
                n="", a="\n\t".join(["{x}", "{y}", "{z}"])))
        f.write(TEMPLATE.format(d="",
                n="t", args="\n\t".join(["{x}"])))
    tool = (configurations.get_tool_definition(FOLDER, 't'))
    assert tool['argument_names'] == ('x', )
    assert tool['tool_name'] == "t"

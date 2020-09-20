import crosscompute.routines as cc


def test_load_tool_configuration_basic(config_file):
    normalized_tool_configuration = cc.load_tool_configuration(config_file)
    assert {
        "id": "add-numbers",
        "input": {
            "templates": [
                {
                    "blocks": [{"id": "a"}, {"id": "b"}],
                    "id": "generated",
                    "name": "Generated",
                }
            ],
            "variables": [
                {"id": "a", "name": "a", "path": "/tmp/a.txt", "view": "number"},
                {"id": "b", "name": "b", "path": "/tmp/b.txt", "view": "number"},
            ],
        },
        "name": "Add Two Numbers",
        "output": {
            "templates": [
                {"blocks": [{"id": "s"}], "id": "generated", "name": "Generated"}
            ],
            "variables": [
                {"id": "s", "name": "s", "path": "/tmp/s.txt", "view": "number"}
            ],
        },
        "slug": "add",
        "version": "0.1.0",
    } == normalized_tool_configuration


def test_load_tool_configuration_templates(config_file_with_templates):
    normalized_tool_configuration = cc.load_tool_configuration(
        config_file_with_templates
    )
    assert {
        "input": {
            "templates": [
                {"blocks": [{"id": "template-a"}], "id": "basic", "name": "Basic"}
            ],
            "variables": [
                {"id": "a", "name": "A", "path": "numbers.json", "view": "number"},
                {"id": "b", "name": "B", "path": "numbers.json", "view": "number"},
            ],
        },
        "name": "Add Numbers",
        "output": {
            "templates": [
                {
                    "blocks": [{"data": {"value": "5"}, "view": "markdown"}],
                    "id": "summary",
                    "name": "Summary",
                }
            ],
            "variables": [
                {"id": "c", "name": "C", "path": "sum.json", "view": "number"}
            ],
        },
        "version": {"name": "0.2.0"},
    } == normalized_tool_configuration

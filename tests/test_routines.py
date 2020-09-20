import crosscompute.routines as cc


def test_load_tool_configuration(config_file):
    normalized_tool_configuration = cc.load_tool_configuration(config_file)
    assert {
        "id": "add-numbers",
        "input": {
            "templates": [
                {"blocks": [{"id": "a"}, {"id": "b"}], "id": "generated", "name": "Generated"}
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

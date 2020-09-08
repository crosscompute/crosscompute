from textwrap import dedent

import pytest
import tempfile


@pytest.fixture
def config_file():
    with tempfile.NamedTemporaryFile("w") as temp:
        temp.write(
            dedent(
                """
            protocol: 0.8.3
            id: add-numbers
            slug: add
            name: Add Two Numbers
            version: 0.1.0
            input: 
                variables:
                    - name: a
                      id: a
                      view: number
                      path: /tmp/a.txt
                    - name: b
                      id: b
                      view: number
                      path: /tmp/b.txt
            output: 
                variables:
                    - name: s
                      id: s
                      view: number
                      path: /tmp/s.txt
            """
            )
        )
        temp.flush()
        yield temp.name

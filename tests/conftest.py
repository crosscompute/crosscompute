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


@pytest.fixture
def config_file_with_templates():
    with tempfile.NamedTemporaryFile("w") as temp:
        temp.write(
            dedent(
                """
            protocol: 0.8.3
            name: Add Numbers
            version:
                name: 0.2.0
            input:
                variables:
                    - id: a
                      name: A
                      view: number
                      path: numbers.json
                    - id: b
                      name: B
                      view: number
                      path: numbers.json
                templates:
                    - id: basic
                      name: Basic
                      blocks:
                        - id: template-a

            output:
                variables:
                    - id: c
                      name: C
                      view: number
                      path: sum.json
                templates:
                    - id: summary
                      name: Summary
                      blocks:
                        - view: markdown
                          data:
                            value: 5
            tests:
                - id: integers
                  name: Add Integers
                  path: tests/integers
                - id: floats
                  name: Add Floats
                  path: tests/floats
            script:
                uri: git@github.com:crosscompute/crosscompute-examples
                folder: add-numbers
                command: bash run.sh
            environment:
                image: docker.io/library/python:slim-buster
                processor: cpu
                memory: tiny
            """
            )
        )
        temp.flush()
        yield temp.name

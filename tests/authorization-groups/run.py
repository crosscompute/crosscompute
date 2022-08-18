import json
from os import getenv
from pathlib import Path


input_folder = Path(getenv(
    'CROSSCOMPUTE_INPUT_FOLDER', 'batches/standard/input'))
output_folder = Path(getenv(
    'CROSSCOMPUTE_OUTPUT_FOLDER', 'batches/standard/output'))
debug_folder = Path(getenv(
    'CROSSCOMPUTE_DEBUG_FOLDER', 'batches/standard/debug'))


output_folder.mkdir(parents=True, exist_ok=True)


with open(input_folder / 'variables.dictionary', 'rt') as f:
    d = json.load(f)
    x = d['x']


try:
    with open(debug_folder / 'identities.dictionary', 'rt') as f:
        d = json.load(f)
        example_role_name = d['example_role_name']
except (OSError, ValueError):
    example_role_name = None
if example_role_name == 'c':
    y = x + 1
elif example_role_name == 'd':
    y = x * 2
else:
    y = x


with open(output_folder / 'variables.dictionary', 'wt') as f:
    d = {'y': y}
    json.dump(d, f)

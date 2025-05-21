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
    y = d['y']


try:
    with open(debug_folder / 'identities.dictionary', 'rt') as f:
        d = json.load(f)
        xx = d['x']
except (OSError, ValueError):
    xx = None
if xx:
    y += xx


with open(output_folder / 'variables.dictionary', 'wt') as f:
    d = {'z': x + y}
    json.dump(d, f)

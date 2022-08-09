import json
from os import getenv
from pathlib import Path
from time import sleep


input_folder = Path(getenv(
    'CROSSCOMPUTE_INPUT_FOLDER', 'batches/standard/input'))
output_folder = Path(getenv(
    'CROSSCOMPUTE_OUTPUT_FOLDER', 'batches/standard/output'))
log_folder = Path(getenv(
    'CROSSCOMPUTE_LOG_FOLDER', 'batches/standard/log'))
debug_folder = Path(getenv(
    'CROSSCOMPUTE_DEBUG_FOLDER', 'batches/standard/debug'))


log_folder.mkdir(parents=True, exist_ok=True)


with open(input_folder / 'variables.dictionary', 'rt') as f:
    d = json.load(f)
    iteration_count = d['iteration_count']
    delay_in_seconds = d['delay_in_seconds']


with open(log_folder / 'log.md', 'wt') as f:
    for i in range(iteration_count):
        print(i)
        print(i, file=f)
        f.flush()
        sleep(delay_in_seconds)


with open(output_folder / 'variables.dictionary', 'wt') as f:
    json.dump({
        'time_in_seconds': iteration_count * delay_in_seconds,
    }, f)

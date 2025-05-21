import json
from pathlib import Path
from sys import argv
from time import sleep, time


input_folder, output_folder, log_folder = [Path(_) for _ in argv[1:]]
log_folder.mkdir(parents=True, exist_ok=True)
t = time()


with open(input_folder / 'variables.dictionary', 'rt') as f:
    d = json.load(f)
    iteration_count = d['iteration_count']
    delay_in_seconds = d['delay_in_seconds']


with open(
    log_folder / 'info.md', 'wt',
) as log_markdown_file:
    for i in range(iteration_count):
        print(i)
        print(f'- <span class="i">{i}</span>', file=log_markdown_file)
        log_markdown_file.flush()
        sleep(delay_in_seconds)


with open(output_folder / 'variables.dictionary', 'wt') as f:
    json.dump({
        'time_in_seconds': time() - t,
    }, f)

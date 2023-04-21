import json
from pathlib import Path
from sys import argv


# Get folder paths from command-line arguments
input_folder, output_folder = [Path(_) for _ in argv[1:]]


# Load input variables from input folder
with (input_folder / 'variables.dictionary').open('rt') as f:
    variables = json.load(f)


# Perform calculation
c = variables['a'] + variables['b']


# Save output variables to output folder
with (output_folder / 'variables.dictionary').open('wt') as f:
    json.dump({'c': c}, f)

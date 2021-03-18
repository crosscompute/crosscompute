import json
from os.path import join
from sys import argv


input_folder, output_folder, log_folder, debug_folder = argv[1:]
value_by_key = json.load(open(join(input_folder, 'numbers.json')))
a = value_by_key['a']
b = value_by_key['b']


output_dictionary = {}
log_dictionary = {}
debug_dictionary = {}


if a < 10:
    output_dictionary['c'] = a + b
    log_dictionary['e'] = a + b
    debug_dictionary['g'] = a + b
if a < 100:
    output_dictionary['d'] = a * b
    log_dictionary['f'] = a * b
    debug_dictionary['h'] = a * b


json.dump(output_dictionary, open(join(
    output_folder, 'properties.json'), 'wt'))
json.dump(log_dictionary, open(join(
    log_folder, 'properties.json'), 'wt'))
json.dump(debug_dictionary, open(join(
    debug_folder, 'properties.json'), 'wt'))

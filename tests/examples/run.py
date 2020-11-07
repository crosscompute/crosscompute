import json
from os.path import join
from sys import argv


input_folder, output_folder = argv[1:3]
value_by_key = json.load(open(join(input_folder, 'numbers.json')))
a = value_by_key['a']
b = value_by_key['b']
d = {'c': a + b}
json.dump(d, open(join(output_folder, 'properties.json'), 'wt'))

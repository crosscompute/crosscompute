import sys


myfile = sys.argv[1]
with open(myfile, 'r') as f:
    for line in f:
        print(line)

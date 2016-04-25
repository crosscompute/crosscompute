import sys

arabic = sys.argv[1]
target_folder = sys.argv[2]
with open(arabic, 'r') as f:
    content = f.read().strip().split(" ")
    print('number of words: %d' % len(content))

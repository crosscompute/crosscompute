import sys


arabic = sys.argv[1]
target_folder = sys.argv[2]

print("my_text_path = " + arabic)
with open(arabic, 'r') as f:
    print(f.read())

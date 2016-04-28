# https://www.maxmind.com/en/free-world-cities-database
import sys
import csv
from os.path import join


points = sys.argv[1]
target_folder = sys.argv[2]
target_folder = join(target_folder, 'points.csv')
with open(target_folder, 'w') as f:
    writer = csv.writer(f)
    with open(points, 'r') as r:
        for line in r:
            writer.writerow(line.split(','))
print('my_geotable_path = %s' % target_folder)

from os.path import basename, join
from sys import argv
target_folder, source_path = argv[1:]
target_path = join(target_folder, 'a')
open(target_path, 'wb').write(open(source_path, 'rb').read())
print('a_path = %s' % target_path)

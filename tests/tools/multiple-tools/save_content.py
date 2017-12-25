import shutil
from os.path import join
from sys import argv
target_folder, source_path = argv[1:]
target_path = join(target_folder, 'a')
shutil.copy(source_path, target_path)
print('a_path = %s' % target_path)

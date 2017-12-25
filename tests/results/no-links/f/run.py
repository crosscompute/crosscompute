import random
import sys
from os.path import join


[
    target_folder,
    subject_text_path,
    verb_text_path,
    object_text_path,
    adverb_text_path
] = sys.argv[1:6]
subjects = open(subject_text_path).read().splitlines()
verbs = open(verb_text_path).read().splitlines()
objects = open(object_text_path).read().splitlines()
adverbs = open(adverb_text_path).read().splitlines()
story_text = '%s %s %s %s' % (
    random.choice(subjects),
    random.choice(verbs),
    random.choice(objects),
    random.choice(adverbs))
print(story_text)
target_path = join(target_folder, 'story.txt')
open(target_path, 'wt').write(story_text)
print('story_text_path = %s' % target_path)

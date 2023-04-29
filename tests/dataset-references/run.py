import json
import re
from os import getenv
from pathlib import Path


output_folder = Path(getenv(
    'CROSSCOMPUTE_OUTPUT_FOLDER', 'batches/standard/output'))
datasets_folder = Path('datasets')
document_path = datasets_folder / 'document.txt'
with document_path.open('rt') as f:
    text = re.sub(r'[^a-zA-Z\s]', '', f.read())
word_count = len(text.split())
with (output_folder / 'variables.dictionary').open('wt') as f:
    json.dump({
        'word_count': word_count,
    }, f)

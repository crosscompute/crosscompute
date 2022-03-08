import os
import sys
import codecs
from crosscompute.tests import run, serve
from os.path import join
from six import BytesIO
from zipfile import ZipFile

from conftest import FOLDER


TEXT = (
    'Each day, I would like to learn and share what I have learned, '
    'in a way that other people can use.')


def test_output_logging(tmpdir, text=TEXT):
    args = str(tmpdir), 'echo', {'x': text}
    r = run(*args)
    assert r['raw_output'] == text
    s = serve(*args)[0]
    assert extract_text(s, 'raw_output-meta') == text


def test_file_name_with_spaces(tmpdir):
    args = str(tmpdir), 'file-name-with-spaces',
    r = run(*args)
    assert r['raw_output'] == 'actions not words'


def test_file_content(tmpdir, file_path='assets/string.txt'):
    file_content = codecs.open(join(
        FOLDER, file_path), encoding='utf-8').read()
    args = str(tmpdir), 'file-content', {'x_txt': file_content}
    s, c = serve(*args)
    assert extract_text(s, 'a-result') == file_content.strip()
    response = c.get(s.find('a', {'class': 'download'})['href'])
    zip_file = ZipFile(BytesIO(response.data))
    assert zip_file.read('a').decode('utf-8') == file_content


def test_target_folder(tmpdir):
    args = str(tmpdir), 'target-folder'
    r = run(*args)
    assert r['raw_output'].startswith(str(tmpdir))


def extract_text(soup, element_id):
    text = soup.find(id=element_id).text.strip()
    if os.name == 'nt' and sys.version_info[0] > 2:
        try:
            text = text.encode('mbcs').decode('utf-8')
        except UnicodeEncodeError:
            pass
    return text

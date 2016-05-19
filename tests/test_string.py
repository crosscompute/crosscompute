import codecs
import tempfile
from crosscompute.tests import run, serve
from os.path import join
from six import StringIO
from zipfile import ZipFile

from conftest import TOOL_FOLDER


TEXT = (
    'Each day, I would like to learn and share what I have learned, '
    'in a way that other people can use.')


def test_stream_logging(tmpdir, text=TEXT):
    args = str(tmpdir), 'echo', {'x': text}
    r = run(*args)
    assert r['standard_output'] == text
    assert r['standard_error'] == text
    s = serve(*args)[0]
    assert s.find(id='standard_output-meta').text.strip() == text
    assert s.find(id='standard_error-meta').text.strip() == text


def test_stream_parsing(tmpdir, text=TEXT):
    args = str(tmpdir), 'assign', {'x': text}
    r = run(*args)
    assert r['standard_outputs']['a'] == text
    assert r['standard_errors']['a'] == text
    s = serve(*args)[0]
    assert s.find(id='a-result').text.strip() == text
    assert s.find(id='a-error').text.strip() == text


def test_file_name_with_spaces(tmpdir):
    args = str(tmpdir), 'file-name-with-spaces',
    r = run(*args)
    assert r['standard_output'] == 'actions not words'


def test_file_content(tmpdir, file_path='assets/string.txt'):
    file_content = codecs.open(join(
        TOOL_FOLDER, file_path), encoding='utf-8').read()
    args = str(tmpdir), 'file-content', {'x_path': file_path}
    s, c = serve(*args)
    assert s.find(id='a-result').text.strip() == file_content.strip()
    response = c.get(s.find('a', {'class': 'download'})['href'])
    zip_file = ZipFile(StringIO(response.data))
    assert zip_file.read('a').decode('utf-8') == file_content


def test_target_folder(tmpdir):
    args = str(tmpdir), 'target-folder'
    r = run(*args)
    assert r['standard_output'].startswith(tempfile.gettempdir())

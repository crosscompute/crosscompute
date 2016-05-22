import os
import sys
from invisibleroads_macros.disk import get_package_folder
from os.path import join


TOOL_FOLDER = join(get_package_folder(__file__), 'tools')


def extract_text(soup, element_id):
    text = soup.find(id=element_id).text.strip()
    if os.name == 'nt' and sys.version_info[0] > 2:
        try:
            text = text.encode('mbcs').decode('utf-8')
        except UnicodeEncodeError:
            pass
    return text

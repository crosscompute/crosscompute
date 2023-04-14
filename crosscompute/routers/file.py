import json
from logging import getLogger
from mimetypes import guess_extension
from pathlib import Path

from fastapi import APIRouter, UploadFile
from invisibleroads_macros_disk import make_random_folder

from ..constants import (
    FILES_FOLDER,
    FILES_ROUTE)


router = APIRouter()


@router.post(FILES_ROUTE, tags=['file'])
async def add_files_json(files: list[UploadFile]):
    file_dictionaries = []
    folder = Path(make_random_folder(FILES_FOLDER))
    for file_index, async_file in enumerate(files):
        name = async_file.filename
        path = folder / str(file_index)
        content_type = async_file.content_type
        with open(path, 'wb') as f:
            f.write(await async_file.read())
        file_dictionaries.append({
            'name': name,
            'type': content_type,
            'size': path.stat().st_size,
            'extension': guess_extension(content_type)})
        L.info(f'saved {name} in {path}')
    with open(folder / 'files.json', 'wt') as f:
        json.dump(sorted(file_dictionaries, key=lambda _: _['name']), f)
    return {'uri': f'/f/{folder.name}'}


L = getLogger(__name__)

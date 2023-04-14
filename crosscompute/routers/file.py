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
    ds = []
    for async_file in files:
        file_folder = Path(make_random_folder(FILES_FOLDER))
        file_name = async_file.filename
        file_path = file_folder / 'file'
        content_type = async_file.content_type
        with open(file_path, 'wb') as f:
            f.write(await async_file.read())
        with open(file_folder / 'file.json', 'wt') as f:
            json.dump({
                'name': file_name,
                'type': content_type,
                'extension': guess_extension(content_type),
            }, f)
        L.info(f'saved {file_name} in {file_path}')
        ds.append({'id': file_folder.name})
    return {'files': ds}


L = getLogger(__name__)

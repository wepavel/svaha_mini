from typing import Any

from fastapi import APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import PlainTextResponse

from app.core.utils import generate_session_id
from app.services.s3 import s3

router = APIRouter()


@router.post('/upload')
async def create_upload_session() -> dict[str, str]:
    session_id = generate_session_id()
    file_presigned_url = s3.generate_presigned_url(file_name=f'{session_id}/music.mp3', file_type='audio/mp3')
    return {'session_id': session_id, 'upload_url': file_presigned_url}


@router.get('/test/{id}', response_class=PlainTextResponse)
async def create_upload_session(id: int) -> Any:
    if id > 10:
        raise HTTPException(status_code=418, detail='Nope!')
    return 'Hello "World"!'

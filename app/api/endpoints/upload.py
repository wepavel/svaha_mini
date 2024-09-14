from fastapi import APIRouter

from app.core.utils import generate_session_id
from app.services.s3 import generate_presigned_url

router = APIRouter()


@router.post('/upload')
async def create_upload_session():
    session_id = generate_session_id()
    file_presigned_url = generate_presigned_url(file_name=f'{session_id}/music.mp3', file_type='audio/mp3')
    return {'session_id': session_id, 'upload_url': file_presigned_url}

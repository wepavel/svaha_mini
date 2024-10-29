from fastapi import APIRouter

from app.core.utils import generate_session_id
from app.services.s3 import s3_manager

router = APIRouter()


@router.post('/download')
async def generate_download_url() -> dict[str, str]:
    session_id = generate_session_id()
    file_presigned_url = s3_manager.generate_presigned_url(file_name=f'{session_id}/music.mp3', file_type='audio/mp3')
    return {'session_id': session_id, 'upload_url': file_presigned_url}


# @router.post('/upload')
# async def upload_file(file: UploadFile = File(...)) -> dict[str, str]:
#     if file.content_type != 'audio/mp3':
#         raise EXC(ErrorCodes.WrongFormat)
#
#     session_id = generate_session_id()
#     file_name = f'{session_id}/music.mp3'
#
#     try:
#         s3.put_object(file_name, file.file, file.size, content_type='audio/mp3')
#         return {"message": "File uploaded successfully", "file_name": file_name}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get('/download/{session_id}')
# async def download_file(session_id: str):
#     file_name = f'{session_id}/music.mp3'
#     try:
#         response = s3.get_object(file_name)
#         content = response.read()
#         return FileResponse(io.BytesIO(content), media_type='audio/mp3', filename='music.mp3')
#     except Exception as e:
#         raise EXC(ErrorCodes.NotFoundError)
#
#
# @router.get('/download-url/{session_id}')
# async def get_download_url(session_id: str) -> dict[str, str]:
#     file_name = f'{session_id}/music.mp3'
#     try:
#         download_url = s3.generate_presigned_url(file_name, http_method='GET')
#         return {"download_url": download_url}
#     except Exception as e:
#         raise HTTPException(status_code=404, detail="File not found")

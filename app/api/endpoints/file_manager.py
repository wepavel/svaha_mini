from fastapi import APIRouter, File, UploadFile, Cookie
from fastapi.responses import RedirectResponse, JSONResponse

from app.core.utils import generate_id
from app.services.s3_async import s3
from app.core.exceptions import EXC, ErrorCodes
from app.core.config import settings
from app.services.redis_service import redis_service
from app.models.task import TaskStatus
from app.services.processing import r_queue
from app.models.session import Session, SessionPublic

from io import BytesIO
from typing import Any
import time

router = APIRouter()

async def get_average_processing_time() -> int:
    return 60  # Average processing time in seconds

@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> JSONResponse:
    """
    Get session id and set it into cookie
    """
    response = JSONResponse(content={})
    if session_id is None:
        session_id = generate_id()

        response.set_cookie(
            key='session_id',
            value=session_id,
            httponly=True,
            samesite='none',
            secure=True,
            max_age=settings.SESSION_EXPIRE_MINUTES,
        )
    else:
        raise EXC(ErrorCodes.SessionAlreadyExists)
    # if session_id not in session_db:
    #     raise HTTPException(status_code=404, detail="Session not found")
    return response


@router.post("/upload-mp3/", response_model=SessionPublic)
async def upload_audio(
        voice: UploadFile = File(...),
        instrumental: UploadFile = File(...),
        session_id: str | None = Cookie(None)
) -> SessionPublic:
    """
    Uploads two MP3 files (voice and instrumental) to S3 storage and create task to
    SVEDENIE

    Parameters:
    - voice (UploadFile): The voice MP3 file to be uploaded.
    - instrumental (UploadFile): The instrumental MP3 file to be uploaded.
    - session_id (str, optional): Session ID for storing files in a specific directory.

    Raises:
    - EXC: If one or both files are missing or not in MP3 format.
    - EXC: If there is an error while uploading files to S3.
    """

    if session_id is None:
        raise EXC(ErrorCodes.SessionNotFound)
    if voice is None or instrumental is None:
        raise EXC(ErrorCodes.ValidationError, details={'reason': 'Two files are required'})
    if not (voice.filename.endswith('.mp3') and instrumental.filename.endswith('.mp3')):
        raise EXC(ErrorCodes.ValidationError, details={'reason': 'Both files must be in MP3 format'})

    position = await redis_service.get_position(session_id)
    if position is not None:
        raise EXC(ErrorCodes.TaskAlreadyExists)

    project_id = generate_id()
    voice_stream = BytesIO(await voice.read())
    voice_stream.seek(0)

    instrumental_stream = BytesIO(await instrumental.read())
    instrumental_stream.seek(0)

    try:
        await s3.upload_bytes_file(voice_stream, f'{session_id}/{project_id}/V.mp3', 'svaha-mini-input')
        await s3.upload_bytes_file(instrumental_stream, f'{session_id}/{project_id}/M.mp3', 'svaha-mini-input')
    except Exception as e:
        # TODO: create new exception for this
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})

    await r_queue.send_to_queue(
        {
            'session_id': session_id,
            'task_id': project_id,
        }
    )
    position = await redis_service.get_position(session_id)
    return SessionPublic(session_id=session_id, position=position)


@router.get("/download-project-result/{project_id}")
async def download_project_result(project_id: str, session_id: str | None = Cookie(None)):
    if session_id is None:
        raise EXC(ErrorCodes.SessionNotFound)
    file_key = f"{session_id}/{project_id}.mp3"
    try:
        file_irl = await s3.get_file_url(file_key, 'svaha-mini-output')
        return RedirectResponse(url=file_irl, status_code=303)
    except Exception as e:
        # TODO: create new exception for this
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})



@router.get('/status', response_model=Session)
async def get_status(session_id: str | None = Cookie(None)) -> Any:
    """
    Get status of current task
    """
    status = await redis_service.get_status(session_id)  # redis.get(f"status:{session_id}")
    if not status:
        raise EXC(ErrorCodes.TaskNotFound)

    position = await redis_service.get_position(session_id)

    estimated_time = None
    download_url = None
    completed_timestamp = None
    if status == TaskStatus.COMPLETED:
        download_url = await redis_service.get_download_url(session_id)
        if not download_url:
            raise EXC(ErrorCodes.CoreFileUploadingError)
        completed_timestamp = await redis_service.get_completed_timestamp(session_id)
    else:
        avg_time = await get_average_processing_time()
        estimated_time = position * avg_time

    return Session(
        session_id=session_id,
        status=status,
        download_url=download_url,
        estimated_time=estimated_time,
        position=position,
        completed_timestamp=completed_timestamp,
        timestamp=time.time(),
    )

@router.get("/available-projects/{project_id}")
async def get_available_projects(session_id: str | None = Cookie(None)):
    if session_id is None:
        raise EXC(ErrorCodes.SessionNotFound)
    try:
        x = await s3.list_objects_with_date(session_id, 'svaha-mini-output')
        y = 0
    except Exception as e:
        # TODO: create new exception for this
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})

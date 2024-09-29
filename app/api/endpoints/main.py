import time
from typing import Any

from fastapi import APIRouter
from fastapi import Cookie
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import EXC
from app.core.utils import generate_session_id
from app.models.session import Session
from app.models.session import SessionPublic
from app.services.processing import send_to_queue
from app.services.redis_service import TaskStatus
from app.services.redis_service import redis_service

# from test_worker import redis

router = APIRouter()

# Mock database
# session_db = {}


async def get_average_processing_time() -> int:
    return 60  # Average processing time in seconds


@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> Any:
    """
    Get session id and set it into cookie
    """
    # if session_id is None:
    session_id = generate_session_id()

    # response = JSONResponse(
    #     content={
    #         # "access_token": security.create_access_token(user_id, expires_delta=access_token_expires),
    #         # "token_type": "bearer"
    #     }
    # )
    response = JSONResponse(content={})
    response.set_cookie(
        key='session_id',
        value=session_id,
        httponly=True,
        samesite='none',
        secure=True,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
    )

    # if session_id not in session_db:
    #     raise HTTPException(status_code=404, detail="Session not found")
    return response


@router.get('/create_task/{task_id}', response_model=SessionPublic)
async def create_task(
    task_id: str,
    session_id: str | None = Cookie(None),
) -> Any:
    """
    Create task for current session
    """
    position = await redis_service.get_position(session_id)
    if position is not None:
        raise EXC(4000, 'Task already exists')
    await send_to_queue(
        {
            'session_id': session_id,
            'task_id': task_id,
        }
    )
    position = await redis_service.get_position(session_id)
    return SessionPublic(session_id=session_id, position=position)


@router.get('/status', response_model=Session)
async def get_status(session_id: str | None = Cookie(None)) -> Any:
    """
    Get status of current task
    """
    status = await redis_service.get_status(session_id)  # redis.get(f"status:{session_id}")
    if not status:
        raise EXC(4000, 'Task not found')

    position = await redis_service.get_position(session_id)

    estimated_time = 0
    download_url = None
    completed_timestamp = None
    if status == TaskStatus.COMPLETED:
        # download_url = f"https://s3-bucket-url/{session_id}/result.mp3"
        # completed_timestamp = await redis.get(f"completed_timestamp:{session_id}")
        completed_timestamp = await redis_service.get_completed_timestamp(session_id)

    else:
        avg_time = await get_average_processing_time()
        estimated_time = position * avg_time

    # await redis_service.delete_task(session_id)

    return Session(
        session_id=session_id,
        status=status,
        # download_url=download_url,
        estimated_time=estimated_time,
        position=position,
        completed_timestamp=completed_timestamp,
        timestamp=time.time(),
    )


@router.delete('/clear')
async def clear() -> Any:
    """
    Clear Redis storage
    """
    await redis_service.clear_storage()


# @router.get("/status/{session_id}", response_model=Session)
# async def get_status(session_id: str):
#     if session_id not in session_db:
#         raise HTTPException(status_code=404, detail="Session not found")
#     return session_db[session_id]
#
#
# @router.post("/upload")
# async def create_upload_session():
#     session_id = generate_session_id()
#     file_presigned_url = generate_presigned_url(file_name=f"{session_id}/music.mp3", file_type="audio/mp3")
#     return {"session_id": session_id, "upload_url": file_presigned_url}

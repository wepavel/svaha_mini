import time
from typing import Any

from fastapi import APIRouter, Cookie
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from app.core.utils import generate_id
from app.models.session import Session, SessionPublic
from app.services.processing import r_queue
from app.services.redis_service import TaskStatus, redis_service, redis_base

# from test_worker import redis

router = APIRouter()


async def get_average_processing_time() -> int:
    return 60  # Average processing time in seconds


@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> Any:
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
        raise EXC(ErrorCode.TaskAlreadyExists)
    await r_queue.send_to_queue(
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
        raise EXC(ErrorCode.TaskNotFound)

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
    await redis_base.clear_storage()


@router.get('/exc_test')
async def exc_test():
    """
    Test exception
    """

    raise EXC(ErrorCode.IncorrUserCreds)

    # json_compatible_item_data = jsonable_encoder('Exception test')


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

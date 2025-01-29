import time
from typing import Any

from fastapi import APIRouter
from fastapi import Cookie
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import EXC
from app.core.exceptions import ErrorCode
from app.core.logging import logger
from app.core.utils import generate_id
from app.schemas.session import Session
from app.schemas.session import SessionPublic
from app.services.processing import r_queue
from app.services.redis_service import TaskStatus
from app.services.redis_service import redis_base
from app.services.redis_service import redis_service

router = APIRouter()


class AvgProcTime:
    def __init__(self):
        self.avg_time = 0  # Average processing time in seconds

    async def set_avg_processing_time(self, time: int) -> None:
        self.avg_time = (self.avg_time + time) / 2

    async def get_avg_processing_time(self) -> int:
        return self.avg_time


avg_time_manager = AvgProcTime()


# async def get_average_processing_time() -> int:
#     return 60  # Average processing time in seconds


@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> JSONResponse:
    # domain: str = Depends(get_client_domain),
    """Get session id and set it into cookie
    """
    logger.info('Hello world!')
    response = JSONResponse(content={})
    if session_id is None:
        session_id = generate_id(datetime_flag=True)

        response.set_cookie(
            key='session_id',
            value=session_id,
            # httponly=False,
            samesite='lax',
            # domain=domain,
            secure=True,
            max_age=settings.SESSION_EXPIRE_MINUTES,
        )
        await redis_service.init_task(session_id)
    else:
        raise EXC(ErrorCode.SessionAlreadyExists)
    # if session_id not in session_db:
    #     raise HTTPException(status_code=404, detail="Session not found")

    # Set custom header for all environments
    response.headers['X-Session-Token'] = session_id

    # Add the custom header to Access-Control-Expose-Headers
    response.headers['Access-Control-Expose-Headers'] = 'X-Session-Token'

    return response


@router.get('/create_task/{task_id}', response_model=SessionPublic)
async def create_task(
    task_id: str,
    session_id: str | None = Cookie(None),
) -> Any:
    """Create task for current session
    """
    position = await redis_service.get_position(session_id)
    if position is not None:
        raise EXC(ErrorCode.TaskAlreadyExists)
    await r_queue.send_to_queue(
        {
            'session_id': session_id,
            'task_id': task_id,
        },
    )
    position = await redis_service.get_position(session_id)
    return SessionPublic(session_id=session_id, position=position)


@router.get('/status/{session_id}', response_model=Session)
async def get_status(session_id: str | None = None) -> Session:
    """Get status of current task
    """
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    # session_data = await redis_service.get_session_data(
    #     session_id, status=True, position=True, completed_timestamp=True, download_url=True,
    # )
    session_data = await redis_service.get_session_data_multiple(
        session_id,
        fields=['status', 'position', 'completed_timestamp', 'download_url'],
    )
    status = session_data.get('status', None)
    if not status:
        raise EXC(ErrorCode.TaskNotFound)

    estimated_time = None
    download_url = None
    completed_timestamp = None
    position = session_data.get('position', 0)
    if TaskStatus(status) == TaskStatus.COMPLETED:
        download_url = session_data.get('download_url', None)
        completed_timestamp = session_data.get('completed_timestamp', None)
    elif TaskStatus(status) not in [TaskStatus.FAILED, TaskStatus.INIT, TaskStatus.UPLOADING]:
        avg_time = await avg_time_manager.get_avg_processing_time()
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


@router.delete('/clear')
async def clear() -> Any:
    """Clear Redis storage
    """
    await redis_base.clear_storage()


@router.get('/exc_test')
async def exc_test():
    """Test exception
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

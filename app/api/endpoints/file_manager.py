from email.quoprimime import unquote
from io import BytesIO
import time
from typing import Any

from fastapi import APIRouter, Cookie, File, UploadFile, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, HTMLResponse
from asyncio import sleep as async_sleep

from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from app.core.utils import generate_id
from app.models.session import Session, SessionPublic
from app.models.task import TaskStatus
from app.services.processing import r_queue
from app.services.redis_service import redis_service
from app.services.s3_async import ClientType, s3
from app.api.ws_manager import ws_manager

import math
from time import time as count_time
import json

router = APIRouter()

CHUNK_SIZE = 1024 * 1024 * 5  # 64 kB
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB



class AvgProcTime:
    def __init__(self):
        self.avg_time = 0 # Average processing time in seconds

    async def set_avg_processing_time(self, time: int) -> None:
        self.avg_time = (self.avg_time + time)/2

    async def get_avg_processing_time(self) -> int:
        return self.avg_time


avg_time_manager = AvgProcTime()


async def get_client_domain(request: Request) -> str:
    def extract_domain(url: str) -> str:
        # Убираем протокол
        domain = url.split("://")[-1]
        # Убираем путь и параметры запроса
        domain = domain.split("/")[0]
        # Убираем порт
        domain = domain.split(":")[0]
        return domain

    origin = request.headers.get("origin")
    if origin:
        return extract_domain(origin)

    referer = request.headers.get("referer")
    if referer:
        return extract_domain(referer)

    return "Unknown"


@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> JSONResponse:
    # domain: str = Depends(get_client_domain),
    """
    Get session id and set it into cookie
    """
    response = JSONResponse(content={})
    if session_id is None:
        session_id = generate_id(datetime_flag=True)

        response.set_cookie(
            key='session_id',
            value=session_id,
            # httponly=False,
            samesite='none',
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
    response.headers["X-Session-Token"] = session_id

    # Add the custom header to Access-Control-Expose-Headers
    response.headers["Access-Control-Expose-Headers"] = "X-Session-Token"

    return response


@router.post('/upload-mp3/', response_model=SessionPublic)
async def upload_audio(
        vocal: UploadFile = File(..., max_size=FILE_MAX_SIZE),
        instrumental: UploadFile = File(..., max_size=FILE_MAX_SIZE),
        session_id: str | None = Cookie(None)
) -> SessionPublic:
    """
    Uploads two MP3 files (voice and instrumental) to S3 storage and create task to
    SVEDENIE

    Parameters:
    - vocal (UploadFile): The vocal MP3 file to be uploaded.
    - instrumental (UploadFile): The instrumental MP3 file to be uploaded.
    - session_id (str, optional): Session ID for storing files in a specific directory.

    Raises:
    - EXC: If one or both files are missing or not in MP3 format.
    - EXC: If there is an error while uploading files to S3.
    """
    if session_id is None:
        raise EXC(ErrorCode.SessionNotFound)

    await redis_service.set_status(session_id, TaskStatus.UPLOADING)

    # Check if audio is incorrect
    vocal_extension = vocal.filename.split('.')[-1].lower()
    instrumental_extension = instrumental.filename.split('.')[-1].lower()
    logger.info(f'Vocal filename: {vocal.filename}; Instrumental filename: {instrumental.filename}')

    if vocal is None or instrumental is None:
        await redis_service.set_status(session_id, TaskStatus.FAILED)
        raise EXC(ErrorCode.ValidationError, details={'reason': 'Two files are required'})

    if vocal_extension not in ALLOWED_EXTENSIONS or instrumental_extension not in ALLOWED_EXTENSIONS:
        await redis_service.set_status(session_id, TaskStatus.FAILED)
        raise EXC(ErrorCode.ValidationError, details={'reason': 'Files must have allowed extensions'})

    # position = await redis_service.get_position(session_id)
    position = await redis_service.get_session_data(session_id, position = True)

    if position is not None:
        raise EXC(ErrorCode.TaskAlreadyExists)

    track_id = generate_id(datetime_flag=True)

    total_size = vocal.size + instrumental.size
    logger.info(f'Vocal size: {vocal.size} | Instrumental size: {instrumental.size}')

    chunks_uploaded = 0
    total_chunks = math.ceil(total_size / CHUNK_SIZE)

    async def upload_file(file: UploadFile, file_key: str, bucket_name: str) -> None:
        nonlocal chunks_uploaded

        async with s3.multipart_upload_context(file_key, bucket_name) as upload_context:
            while contents := await file.read(CHUNK_SIZE):
                await upload_context.upload_part(contents)

                await redis_service.set_progress(session_id, int(chunks_uploaded*100/total_chunks))
                chunks_uploaded += 1

    await redis_service.set_progress(session_id, 0)
    await upload_file(vocal, f'{session_id}/{track_id}/V.mp3', 'svaha-mini-input')
    await upload_file(instrumental, f'{session_id}/{track_id}/M.mp3', 'svaha-mini-input')

    # Send task to RabbitMQ/Redis
    message = {
        'session_id': session_id,
        'task_id': track_id,
    }
    if not await r_queue.send_to_queue(message):
        redis_service.set_status(session_id, TaskStatus.FAILED)
        raise EXC(ErrorCode.DbError)

    position = await redis_service.get_session_data(session_id, position=True)

    return SessionPublic(session_id=session_id, position=position)

# @router.get("/download-project-result")
# async def download_project_result(session_id: str | None = Cookie(None)):
#     if session_id is None:
#         raise EXC(ErrorCodes.SessionNotFound)
#
#     last_track = await s3.get_latest_subfolder(f'{session_id}/', 'svaha-mini-output')
#     if not last_track:
#         raise EXC(ErrorCodes.CoreFileUploadingError)
#
#     file_url = f'https://s3.machine-prod.ru/svaha-mini-output/{last_track}R.mp3'
#
#     return {"download_url": file_url}
#         #     file_irl = await s3.get_file_url(file_key, 'svaha-mini-output')
#     #     return RedirectResponse(url=file_irl, status_code=303)
#     # except Exception as e:
#     #     # TODO: create new exception for this
#     #     raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/status', response_model=Session)
async def get_status(session_id: str | None = Cookie(None)) -> Any:
    """
    Get status of current task
    """
    session_data = await redis_service.get_session_data(
        session_id,
        status = True,
        position = True,
        completed_timestamp=True,
        download_url=True
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
    elif (TaskStatus(status) != TaskStatus.FAILED and
          TaskStatus(status) != TaskStatus.INIT and
          TaskStatus(status) != TaskStatus.UPLOADING):
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


# async def send_task_status(websocket: WebSocket, session_id: str):
#
#     try:
#         while True:
#             session_data = await redis_service.get_session_data(
#                 session_id,
#                 status = True,
#                 progress= True,
#                 position = True,
#             )
#
#             await websocket.send_json({
#                 'status': session_data.get('status', None),
#                 'progress': session_data.get('progress', None),
#                 'position': session_data.get('position', None),
#             })
#
#             await async_sleep(0.1)
#     except WebSocketDisconnect:
#         logger.info(f'Websocket accepted: session_id={session_id}')
#         raise


@router.websocket('/ws-status')
async def websocket_endpoint(websocket: WebSocket, session_id: str | None = Cookie(None)):
    await ws_manager.connect(websocket, session_id)
    if session_id is None:
        await ws_manager.send_personal_message(websocket, {"error": "Session not found"})

    try:
        while True:
            session_data = await redis_service.get_session_data(
                session_id,
                status = True,
                progress= True,
                position = True,
            )

            await ws_manager.send_personal_message(websocket, session_data)

            await async_sleep(0.1)
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)


    # await websocket.accept()
    # if session_id is None:
    #     await websocket.send_json({"error": "Session not found"})
    #     # await websocket.close()
    # else:

    # await send_task_status(websocket, session_id)

# async def event_generator(session_id: str):
#     while True:
#         await async_sleep(0.1)
#         status = await redis_service.get_status(session_id)
#         if not session_id:
#             yield "data: {\"error\": \"Session not found\"}\n\n"
#             # break
#         if not status:
#             yield "data: {\"error\": \"Task not found\"}\n\n"
#             # break
#
#         yield f"data: {{\"status\": \"{status}\", \"progress\": \"{await redis_service.get_progress(session_id)}\"}}\n\n"
# async def event_generator(session_id: str):
#     previous_status = None
#
#     while True:
#         await async_sleep(0.1)
#         status = await redis_service.get_status(session_id)
#
#         if not session_id:
#             data = {"error": "Session not found"}
#             yield f"data: {json.dumps(data)}\n\n"
#             # break
#         elif not status:
#             data = {"error": "Task not found"}
#             yield f"data: {json.dumps(data)}\n\n"
#             # break
#         else:
#             if status != previous_status:
#                 previous_status = status
#                 data = {
#                     "status": status,
#                     "progress": await redis_service.get_progress(session_id)
#                 }
#                 yield f"data: {json.dumps(data)}\n\n"

# @router.get('/sse-status')
# async def sse_endpoint(session_id: str | None = Cookie(None)):
#     if session_id is None:
#         data =
#         yield f"data: {json.dumps(data)}\n\n"
# @router.get("/sse-status")
# async def sse_endpoint(session_id: str | None = Cookie(None)):
#     # if session_id is None:
#     #     return StreamingResponse("data: {\"error\": \"Session not found\"}\n\n", media_type="text/event-stream")
#     async def generate_message(session_id) -> json:
#         session_data = await redis_service.get_session_data(
#             session_id,
#             status=True,
#             progress=True,
#             position=True,
#         )
#
#     async def event_generator(session_id: str):
#         previous_status = None
#
#         while True:
            # await async_sleep(0.1)
            # status = await redis_service.get_status(session_id)
            #
            # if not session_id:
            #     data = {"error": "Session not found"}
            #     yield f"data: {json.dumps(data)}\n\n"
            #     # break
            # elif not status:
            #     data = {"error": "Task not found"}
            #     yield f"data: {json.dumps(data)}\n\n"
            #     # break
            # else:
            #     if status != previous_status:
            #         previous_status = status
            #         data = {
            #             "status": status,
            #             "progress": await redis_service.get_progress(session_id)
            #         }
            #         yield f"data: {json.dumps(data)}\n\n"

    # return StreamingResponse(event_generator(session_id), media_type="text/event-stream")


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Documentation</title>
    </head>
    <body>
        <h1>WebSocket Endpoint</h1>
        <p>This is a WebSocket endpoint for real-time communication.</p>
        <p>To connect to the WebSocket, use the following URL:</p>
        <pre>wss://wss.machine-prod.ru/ws</pre>
        <p>The WebSocket endpoint supports the following messages:</p>
        <ul>
            <li><code>{"type": "subscribe", "channel": "events"}</code> - Subscribe to the "events" channel.</li>
            <li><code>{"type": "unsubscribe", "channel": "events"}</code> - Unsubscribe from the "events" channel.</li>
        </ul>
    </body>
</html>
"""

@router.get("/ws-docs", response_class=HTMLResponse, include_in_schema=False)
async def get_ws_docs():
    return html

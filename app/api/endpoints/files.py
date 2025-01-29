import math
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter
from fastapi import File
from fastapi import Request
from fastapi import UploadFile

from app.api.sse_eventbus import event_bus
from app.core.exceptions import EXC
from app.core.exceptions import ErrorCode
from app.core.logging import logger
from app.core.utils import generate_id
from app.schemas.events import Event
from app.schemas.events import EventData
from app.schemas.events import NotificationType
from app.schemas.events import Position
from app.schemas.session import SessionPublic
from app.schemas.task import TaskStatus
from app.services.processing import r_queue
from app.services.redis_service import redis_service
from app.services.s3_async import ClientType
from app.services.s3_async import s3

router = APIRouter()

CHUNK_SIZE = 1024 * 1024 * 5  # 64 kB
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


async def get_client_domain(request: Request) -> str:
    def extract_domain(url: str) -> str:
        # Убираем протокол
        domain = url.split('://')[-1]
        # Убираем путь и параметры запроса
        domain = domain.split('/')[0]
        # Убираем порт
        domain = domain.split(':')[0]
        return domain

    origin = request.headers.get('origin')
    if origin:
        return extract_domain(origin)

    referer = request.headers.get('referer')
    if referer:
        return extract_domain(referer)

    return 'Unknown'


@router.post('/upload-old/{session_id}', response_model=SessionPublic)
async def upload_audio(
    session_id: str,
    vocal: UploadFile = File(..., max_size=FILE_MAX_SIZE),
    instrumental: UploadFile = File(..., max_size=FILE_MAX_SIZE),
) -> SessionPublic:
    """Uploads two MP3 files (voice and instrumental) to S3 storage and create task to
    SVEDENIE

    Parameters
    ----------
    - vocal (UploadFile): The vocal MP3 file to be uploaded.
    - instrumental (UploadFile): The instrumental MP3 file to be uploaded.
    - session_id (str, optional): Session ID for storing files in a specific directory.

    Raises
    ------
    - EXC: If one or both files are missing or not in MP3 format.
    - EXC: If there is an error while uploading files to S3.

    """
    # cur_status = await redis_service.get_session_data(session_id, status=True)
    # cur_status = cur_status.get('status')
    cur_status = await redis_service.get_session_data_single(session_id, field='status')
    # todo simplify
    # if cur_status == TaskStatus.IN_PROGRESS.value \
    #     or cur_status == TaskStatus.UPLOADING.value \
    #     or cur_status == TaskStatus.QUEUED.value:
    #     raise EXC(ErrorCode.TaskAlreadyExists)

    if TaskStatus(cur_status) in [TaskStatus.IN_PROGRESS, TaskStatus.UPLOADING, TaskStatus.QUEUED]:
        raise EXC(ErrorCode.TaskAlreadyExists)

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
    # position = await redis_service.get_session_data(session_id, position=True)
    # position = position.get('position')
    position = await redis_service.get_session_data_single(session_id, field='position')

    if position is not None:
        raise EXC(ErrorCode.TaskAlreadyExists)

    track_id = generate_id(datetime_flag=True)

    total_size = vocal.size + instrumental.size
    logger.info(f'Vocal size: {vocal.size} | Instrumental size: {instrumental.size}')

    chunks_uploaded = 0
    total_chunks = math.ceil(total_size / CHUNK_SIZE)

    async def upload_file(file: UploadFile, file_key: str, bucket_name: str) -> None:
        nonlocal chunks_uploaded

        async with s3.multipart_upload_context(file_key, bucket_name, ClientType.WRITER) as upload_context:
            while contents := await file.read(CHUNK_SIZE):
                await upload_context.upload_part(contents)

                event = Event(
                    name='progress',
                    data=EventData(
                        id=session_id,
                        message=f'Progress state: {int(chunks_uploaded * 100 / total_chunks)}',
                        notification_type=NotificationType.INFO,
                        position=Position.CENTER),
                )
                await event_bus.post(session_id, event)
                await redis_service.set_progress(session_id, int(chunks_uploaded * 100 / total_chunks))
                chunks_uploaded += 1

    await redis_service.set_progress(session_id, 0)

    await upload_file(vocal, f'{session_id}/{track_id}/V.mp3', 'svaha-mini-input')
    await upload_file(instrumental, f'{session_id}/{track_id}/M.mp3', 'svaha-mini-input')

    event = Event(
        name='progress',
        data=EventData(id=session_id, message='Progress state: 100',
                       notification_type=NotificationType.INFO, position=Position.CENTER))
    await event_bus.post(session_id, event)

    event = Event(
        name='progress',
        data=EventData(id=session_id, message='Upload have been succesfully completed',
                       notification_type=NotificationType.SUCCESS, position=Position.CENTER))
    await event_bus.post(session_id, event)

    # Send task to RabbitMQ/Redis
    message = {
        'session_id': session_id,
        'task_id': track_id,
    }
    if not await r_queue.send_to_queue(message):
        redis_service.set_status(session_id, TaskStatus.FAILED)
        raise EXC(ErrorCode.DbError)

    # position = await redis_service.get_session_data(session_id, position=True)
    position = await redis_service.get_session_data_single(session_id, field='position')

    return SessionPublic(session_id=session_id, position=position)


@router.post('/upload/{session_id}/{track_id}/{type}', response_model=SessionPublic)
async def upload(
        request: Request,
        type: str,
        session_id: str,
        track_id: str,
) -> SessionPublic:
    cur_status = await redis_service.get_session_data_single(session_id, field='status')

    if TaskStatus(cur_status) in [TaskStatus.IN_PROGRESS, TaskStatus.QUEUED]:  # todo: We need TaskStatus.UPLOADING?
        raise EXC(ErrorCode.TaskAlreadyExists)

    await redis_service.set_status(session_id, TaskStatus.UPLOADING)

    content_length = int(request.headers.get('content-length', 0))
    content_type = request.headers.get('content-type')

    content_disposition = request.headers.get('content-disposition', '')
    filename = ''
    if 'filename' in content_disposition:
        filename = content_disposition.split('filename=')[1].strip('"')
        filename = unquote(filename)

    if not filename:
        filename = 'uploaded_audio.mp3'

    async def read_in_chunks(stream: AsyncGenerator[bytes | None], chunk_size: int) -> AsyncGenerator[
        int | bytearray, Any]:
        buffer = bytearray()
        async for data in stream:
            buffer.extend(data)
            while len(buffer) >= chunk_size:
                yield buffer[:chunk_size]
                buffer = buffer[chunk_size:]
        if buffer:
            yield buffer

    total_read = 0
    count = 0

    async for chunk in read_in_chunks(request.stream(), CHUNK_SIZE):
        count += 1
        total_read += len(chunk)
        logger.info(f'Chunk loaded: {total_read}/{content_length} bytes, count: {count}')

    return SessionPublic(session_id='sassss', position=14)


# @router.post("/send_payment_message")
# async def send_payment_message(session_id: str | None = Cookie(None)):
#     status = await payment_message(
#         session_id,
#         f'Hello {session_id} from payment message',
#         NotificationType.INFO,
#         Position.RIGHT_BOTTOM
#     )
#     return {"status": status}


# @router.get("/status")
# async def get_status():
#     return {"status": await event_bus.get_status()}
#
# @router.post("/set_status")
# async def set_status(status: str):
#     new_status = await event_bus.set_status(status)
#     return {"status": new_status}


#     # return StreamingResponse(event_generator(), media_type="text/event-stream")


# @router.post("/shutdown/{user_id}")
# async def shutdown(user_id: str, background_tasks: BackgroundTasks):
#     background_tasks.add_task(event_bus.shutdown, user_id)
#     return {"message": f"Shutdown initiated for user {user_id}"}
#
# @router.get("/user_messages/{user_id}")
# async def get_user_messages(user_id: str):
#     messages = await event_bus.get_user_messages(user_id)
#     return {"messages": messages}


# @router.get("/ws-docs", response_class=HTMLResponse, include_in_schema=True)
# async def get_ws_docs():
#     return html

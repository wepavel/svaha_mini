from asyncio import sleep as async_sleep
import math
import time
from typing import Any

from fastapi import APIRouter, Cookie, File, Request, UploadFile, WebSocket, Path
from typing import Annotated
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from app.api.sse_eventbus import NotificationType, Position, Event, EventData, broadcast_msg, event_bus, wg_msg
from app.api.ws_manager import ws_manager
from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from app.core.utils import generate_id
from app.models.session import Session, SessionPublic
from app.models.task import TaskStatus
from app.services.processing import r_queue
from app.services.redis_service import redis_service
from app.services.s3_async import ClientType, s3
import asyncio
from urllib.parse import unquote
router = APIRouter()

CHUNK_SIZE = 1024 * 1024 * 5  # 64 kB
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


class AvgProcTime:
    def __init__(self):
        self.avg_time = 0  # Average processing time in seconds

    async def set_avg_processing_time(self, time: int) -> None:
        self.avg_time = (self.avg_time + time) / 2

    async def get_avg_processing_time(self) -> int:
        return self.avg_time


avg_time_manager = AvgProcTime()


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


@router.get('/session')
async def get_session(session_id: str | None = Cookie(None)) -> JSONResponse:
    # domain: str = Depends(get_client_domain),
    """
    Get session id and set it into cookie
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


@router.post('/upload-mp3/{session_id}', response_model=SessionPublic)
async def upload_audio(
    session_id: str,
    vocal: UploadFile = File(..., max_size=FILE_MAX_SIZE),
    instrumental: UploadFile = File(..., max_size=FILE_MAX_SIZE),
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

    cur_status = await redis_service.get_session_data(session_id, status=True)
    if cur_status == TaskStatus.IN_PROGRESS.value \
        or cur_status == TaskStatus.UPLOADING.value \
        or cur_status == TaskStatus.QUEUED.value:
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
    position = await redis_service.get_session_data(session_id, position=True)

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
        data=EventData(id=session_id, message=f'Progress state: 100',
                       notification_type=NotificationType.INFO, position=Position.CENTER))
    await event_bus.post(session_id, event)

    event = Event(
        name='progress',
        data=EventData(id=session_id, message=f'Upload have been succesfully completed',
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

    position = await redis_service.get_session_data(session_id, position=True)

    return SessionPublic(session_id=session_id, position=position)

async def read_in_chunks(stream, chunk_size):
    buffer = bytearray()
    async for data in stream:
        buffer.extend(data)
        while len(buffer) >= chunk_size:
            yield buffer[:chunk_size]
            buffer = buffer[chunk_size:]
    if buffer:
        yield buffer

@router.post('/true-upload', response_model=SessionPublic)
async def true_upload(
        request: Request,
        # type: str,
        # session_id: str
) -> SessionPublic:
    content_length = int(request.headers.get('content-length', 0))
    content_type = request.headers.get('content-type')

    content_disposition = request.headers.get('content-disposition', '')
    filename = ''
    if 'filename' in content_disposition:
        filename = content_disposition.split('filename=')[1].strip('"')
        filename = unquote(filename)

    if not filename:
        filename = 'uploaded_audio.mp3'



    total_read = 0
    # async for chunk in request.stream():
    #     total_read += len(chunk)
    #     logger.info(f'Chunk loaded: {total_read}/{content_length} bytes')

    async for chunk in read_in_chunks(request.stream(), CHUNK_SIZE):
        total_read += len(chunk)
        logger.info(f'Chunk loaded: {total_read}/{content_length} bytes')


    return SessionPublic(session_id='sassss', position=14)


@router.post('/upload-mp3-test', response_model=SessionPublic)
async def upload_audio_test(
    vocal: UploadFile = File(..., max_size=FILE_MAX_SIZE),
    instrumental: UploadFile = File(..., max_size=FILE_MAX_SIZE),
    session_id: str | None = Cookie(None),
) -> SessionPublic:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return await upload_audio(session_id, vocal, instrumental)


@router.get('/mock-progress/{session_id}')
async def mock_progress(session_id: str):
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    for i in range(10):
        event = Event(
            name='progress',
            data=EventData(
                id=session_id,
                message=f'Progress state: {int(i * 100 / 10)}',
                notification_type=NotificationType.INFO,
                position=Position.CENTER),
        )
        await event_bus.post(session_id, event)
        await asyncio.sleep(1)

    event = Event(
        name='progress',
        data=EventData(
            id=session_id,
            message=f'Progress state: 100',
            notification_type=NotificationType.INFO,
            position=Position.CENTER),
    )
    await event_bus.post(session_id, event)
    event = Event(name='progress', data=EventData(id=session_id, message=f'Upload have been succesfully completed',
                                                 notification_type=NotificationType.SUCCESS, position=Position.CENTER))
    await event_bus.post(session_id, event)


@router.get('/mock-progress-test')
async def mock_progress_test(session_id: str | None = Cookie(None)):
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return await mock_progress(session_id)

@router.get('/track-settings')
async def get_track_settings() -> JSONResponse:
    settings = {
        'instrumental_settings': [
            {'id': 'bitcrusher', 'title': 'Bitcrusher', 'value': False, 'type': 'checkbox'},
        ],
        'voice_settings': [
            {
                'id': 'volume',
                'title': 'Volume',
                'type': 'slider',
                'value': 0,
                'min': -80,
                'max': 10,
                'step': 1,
                'startPoint': 0,
            },
            {
                'id': 'tonal_balance',
                'title': 'Tonal balance',
                'type': 'slider',
                'value': 50,
                'min': 0,
                'max': 100,
                'step': 1,
                'startPoint': 50,
            },
            {
                'id': 'hardness',
                'title': 'Hardness',
                'type': 'slider',
                'value': 7,
                'min': 0,
                'max': 10,
                'step': 1,
                'startPoint': 5,
            },
            {
                'id': 'echo',
                'title': 'Echo',
                'type': 'slider',
                'value': 10,
                'min': 0,
                'max': 10,
                'step': 1,
                'startPoint': 0,
            },
            {'id': 'autotune', 'title': 'Autotune', 'value': False, 'type': 'checkbox'},
        ],
        'style_settings': [
            {'id': 'foo', 'title': 'Foo', 'value': True, 'type': 'button'},
            {'id': 'bar', 'title': 'Bar', 'value': False, 'type': 'button'},
            {'id': 'baz', 'title': 'Baz', 'value': False, 'type': 'button'},
        ],
    }

    return JSONResponse(content=settings)


@router.get('/status/{session_id}', response_model=Session)
async def get_status(session_id: str | None = None) -> Session:
    """
    Get status of current task
    """
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    session_data = await redis_service.get_session_data(
        session_id, status=True, position=True, completed_timestamp=True, download_url=True
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
    elif (
        TaskStatus(status) != TaskStatus.FAILED
        and TaskStatus(status) != TaskStatus.INIT
        and TaskStatus(status) != TaskStatus.UPLOADING
    ):
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


@router.websocket('/ws-status')
async def websocket_endpoint(websocket: WebSocket, session_id: str | None = Cookie(None)):
    await ws_manager.connect(websocket, session_id)
    if session_id is None:
        await ws_manager.send_personal_message(websocket, {'error': 'Session not found'})

    try:
        while True:
            session_data = await redis_service.get_session_data(
                session_id,
                status=True,
                progress=True,
                position=True,
            )

            await ws_manager.send_personal_message(websocket, session_data)

            await async_sleep(1)
    finally:
        ws_manager.disconnect(session_id)


@router.get('/active-connections')
async def get_active_connections() -> dict[str, Any]:
    """
    Получить список активных SSE подключений.
    Возвращает словарь, где ключ - это user_id, а значение - количество активных подключений для этого пользователя.
    """
    # Здесь можно добавить проверку прав доступа, если это необходимо
    active_connections = await event_bus.get_active_connections()
    return active_connections


# @router.post("/send_payment_message")
# async def send_payment_message(session_id: str | None = Cookie(None)):
#     status = await payment_message(
#         session_id,
#         f'Hello {session_id} from payment message',
#         NotificationType.INFO,
#         Position.RIGHT_BOTTOM
#     )
#     return {"status": status}


@router.post('/send-progress-message/{progress}/{session_id}')
async def send_progress_message(progress: int, session_id: str) -> None:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    event = Event(
        name='progress',
        data=EventData(
            id=session_id,
            message=f'Progress state: {progress}',
            notification_type=NotificationType.INFO,
            position=Position.CENTER),
    )

    await event_bus.post(session_id, event)


@router.post('/send-progress-message-test/{progress}')
async def send_progress_message_test(progress: int, session_id: str | None = Cookie(None)) -> None:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    await send_progress_message(progress, session_id)


@router.post('/send-wg-message/{session_id}')
async def send_wg_message(session_id: str) -> dict[str, Any]:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    status = await wg_msg(
        session_id, f'Hello {session_id} from wg message', NotificationType.INFO, Position.RIGHT_BOTTOM
    )
    return {'status': status}

@router.post('/send-wg-message-test')
async def send_wg_message_test(session_id: str | None = Cookie(None)) -> dict[str, Any]:

    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    return await send_wg_message(session_id)


@router.post('/send-msg-to-all/{msg}')
async def send_msg_to_all(msg: str):
    status = await broadcast_msg(
        msg,
        NotificationType.INFO,
    )
    return {'status': status}

# @router.get("/status")
# async def get_status():
#     return {"status": await event_bus.get_status()}
#
# @router.post("/set_status")
# async def set_status(status: str):
#     new_status = await event_bus.set_status(status)
#     return {"status": new_status}

@router.get('/sse-status/{session_id}')
async def listen_events(request: Request, session_id: str):

    if not session_id:
        raise EXC(ErrorCode.Unauthorized)

    client_host = request.client.host
    logger.info(f'SSE connection established for session {session_id} from {client_host}')
    await event_bus.add_connection(session_id, connection_info={'client_host': client_host})

    async def event_generator():
        try:
            async for event in event_bus.listen(session_id):
                yield f'data: {event}\n\n'
            # while True:
            #     if await request.is_disconnected():
            #         logger.info(f"Client disconnected for session {session_id} from {client_host}")
            #         break
            #
            #     try:
            #     event = await asyncio.wait_for(event_bus.listen(session_id))
            #     yield f"data: {event}\n\n"
            # except asyncio.TimeoutError:
            #     # Отправка heartbeat каждые 15 секунд
            #     yield f"event: heartbeat\ndata: ping\n\n"
            #     break
        except PermissionError as e:
            yield f'event: error\ndata: {e!s}\n\n'
        except Exception:
            yield 'event: error\ndata: An unexpected error occurred\n\n'
            logger.exception('Error in SSE stream')
        finally:
            await event_bus.remove_connection(session_id)
            logger.info(f'SSE connection closed for session {session_id} from {client_host}')

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        background=BackgroundTask(
            lambda: logger.info(f'2) SSE connection fully closed for session {session_id} from {client_host}')
        ),
    )



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


def html(user_id):

    p0 = """<!DOCTYPE html>
<html>
    <head>
        <title>SSE Listener</title>
    </head>
    <style>
    html * {
      font-size: 12px !important;
      color: #0f0 !important;
      font-family: Andale Mono !important;
      background-color: #000;
    }

    </style>
            """
    p2 = f"""
    <body>
        <h1>EventSource Of User {user_id}</h1>
        <script>
            let eventSource;
            // EventSource;
            // WebSocket
            eventSource = new EventSource('https://api.machine-prod.ru/sse/v1/files/sse-status/{user_id}');"""
    p3 = """
              eventSource.onopen = function(e) {
                log("Event: open");
              };

              eventSource.onerror = function(e) {
                log("Event: error");
                if (this.readyState == EventSource.CONNECTING) {
                  log(`Reconnecting (readyState=${this.readyState})...`);
                } else {
                  log("Error.");
                }
              };
              

              eventSource.addEventListener('test', function(e) {
                log("Event: test, data: " + e.data);
              });

              eventSource.onmessage = function(e) {
                log("Event: message, data: " + e.data);
              };
              
              
            //}

            function stop() {
              eventSource.close();
              log("Disconnected");
            }

            function log(msg) {
              let time = new Date()
              let timeval = time.getHours() + ':' + time.getMinutes() + ':' + time.getSeconds() + '  ';
              logElem.innerHTML = timeval + msg + "<br>" + logElem.innerHTML;
              //document.documentElement.scrollTop = 99999999;
            }
            </script>

            <!-- <button onclick="start()">start</button> -->
            <button onclick="log('stop')">stop</button>
            <div id="logElem" style="margin: 6px 0"></div>

            <!-- <button onclick="stop()">Stop</button> -->

    </body>
</html>
"""
    return p0 + p2 + p3


def html_ws(user_id):
    p0 = """<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>
    </head>
    <style>
    html * {
      font-size: 12px !important;
      color: #0f0 !important;
      font-family: Andale Mono !important;
      background-color: #000;
    }
    </style>
    """
    p2 = f"""
    <body>
        <h1>WebSocket Of User {user_id}</h1>
        <script>
            let socket;

            function connect() {{
                socket = new WebSocket('wss://api.machine-prod.ru/ws/v1/files/ws-status{user_id}');
    """
    p3 = """
                socket.onopen = function(e) {
                    log("Connection established");
                };

                socket.onmessage = function(event) {
                    log("Received data: " + event.data);
                };

                socket.onerror = function(error) {
                    log("WebSocket Error: " + error.message);
                };

                socket.onclose = function(event) {
                    if (event.wasClean) {
                        log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
                    } else {
                        log('Connection died');
                    }
                };
            }

            function stop() {
                if (socket) {
                    socket.close();
                    log("Disconnected");
                }
            }

            function log(msg) {
                let time = new Date()
                let timeval = time.getHours() + ':' + time.getMinutes() + ':' + time.getSeconds() + '  ';
                logElem.innerHTML = timeval + msg + "<br>" + logElem.innerHTML;
            }

            // Автоматически подключаемся при загрузке страницы
            connect();
        </script>

        <button onclick="stop()">Stop</button>
        <button onclick="connect()">Reconnect</button>
        <div id="logElem" style="margin: 6px 0"></div>

    </body>
</html>
"""
    return p0 + p2 + p3




@router.get('/get-user-ws/{session_id}')
async def get_ws(session_id: str) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html_ws(session_id))


@router.get('/get-user-ws-test')
async def get_ws(session_id: str | None = Cookie(None)) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html_ws(session_id))

@router.get('/get-user-sse/{session_id}')
async def get_sse(session_id: str) -> HTMLResponse:

    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html(session_id))


@router.get('/get-user-sse-test')
async def get_sse_test(session_id: str | None = Cookie(None)) -> HTMLResponse:

    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    return HTMLResponse(html(session_id))
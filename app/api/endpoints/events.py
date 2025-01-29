import asyncio
from typing import Any

from fastapi import APIRouter
from fastapi import Cookie
from fastapi import Request
from fastapi import WebSocket
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.api.sse_eventbus import event_bus
from app.api.ws_manager import ws_manager
from app.core.exceptions import EXC
from app.core.exceptions import ErrorCode
from app.core.logging import logger
from app.services.redis_service import redis_service

router = APIRouter()


@router.get('/sse/{session_id}')
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
        except Exception as e:
            yield 'event: error\ndata: An unexpected error occurred\n\n'
            logger.exception(f'Error in SSE stream: {e}')
        finally:
            await event_bus.remove_connection(session_id)
            logger.info(f'SSE connection closed for session {session_id} from {client_host}')

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        background=BackgroundTask(
            lambda: logger.info(f'2) SSE connection fully closed for session {session_id} from {client_host}'),
        ),
    )


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, session_id: str | None = Cookie(None)):
    await ws_manager.connect(websocket, session_id)
    if session_id is None:
        await ws_manager.send_personal_message(websocket, {'error': 'Session not found'})

    try:
        while True:
            session_data = await redis_service.get_session_data_multiple(
                session_id,
                fields=['status', 'progress', 'position'],
            )

            await ws_manager.send_personal_message(websocket, session_data)

            await asyncio.sleep(1)
    finally:
        ws_manager.disconnect(session_id)


@router.get('/active-connections')
async def get_active_connections() -> dict[str, Any]:
    """Получить список активных SSE подключений.
    Возвращает словарь, где ключ - это user_id, а значение - количество активных подключений для этого пользователя.
    """
    # Здесь можно добавить проверку прав доступа, если это необходимо
    active_connections = await event_bus.get_active_connections()
    return active_connections

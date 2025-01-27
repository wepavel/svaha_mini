from fastapi.responses import HTMLResponse
from app.core.exceptions import EXC, ErrorCode
from fastapi import APIRouter, Cookie
from app.api.sse_eventbus import NotificationType, Position, Event, EventData, event_bus, broadcast_msg, wg_msg
import asyncio
from typing import Any

router = APIRouter()

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

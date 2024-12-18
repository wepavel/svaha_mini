from datetime import datetime
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest

from app.models.task import TaskStatus
from app.services.redis_service import Redis


@pytest.fixture
def mock_redis() -> AsyncMock:
    with patch('aioredis.Redis') as mock:
        instance = mock.return_value
        instance.pipeline.return_value.__aenter__.return_value = AsyncMock(return_value=instance)
        instance.pipeline.return_value.__aexit__.return_value = AsyncMock(return_value=None)
        return instance


@pytest.fixture
def redis_service(mock_redis: AsyncMock) -> Redis:
    service = Redis()
    service.redis = mock_redis
    return service


@pytest.fixture
def mock_datetime() -> AsyncGenerator[Any, None]:
    fixed_time = 1729106781.695754
    with patch('app.services.redis_service.datetime') as mock_dt:
        mock_dt.now.return_value = datetime.fromtimestamp(fixed_time)
        yield mock_dt, fixed_time


# @pytest.mark.asyncio
# async def test_create_task(redis_service: Redis, mock_datetime: Any) -> None:
#     session_id = 'test_session'
#     track_id = 'test_track'
#
#     mock_dt, fixed_time = mock_datetime
#     with mock_dt:
#         await redis_service.create_task(session_id, track_id)
#         # Check that the correct Redis commands were called
#         pipeline = redis_service.redis.pipeline.return_value.__aenter__.return_value
#
#         pipeline.rpush.assert_called_once_with('processing_queue', session_id, track_id)
#         pipeline.hset.assert_called_once()
#         pipeline.hset.assert_called_once_with(
#             f'session:{session_id}', mapping={'status': TaskStatus.QUEUED, 'timestamp': fixed_time}
#         )
#         pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_status(redis_service: Redis) -> None:
    session_id = 'test_session'
    expected_status = TaskStatus.QUEUED
    redis_service.redis.hget = AsyncMock(return_value=expected_status)

    status = await redis_service.get_status(session_id)

    redis_service.redis.hget.assert_awaited_once_with(f'session:{session_id}', 'status')
    assert status == expected_status


@pytest.mark.asyncio
async def test_get_position(redis_service: Redis) -> None:
    session_id = 'test_session'
    expected_position = 1
    redis_service.redis.lpos = AsyncMock(return_value=expected_position)

    position = await redis_service.get_position(session_id)

    redis_service.redis.lpos.assert_awaited_once_with('processing_queue', session_id)
    assert position == expected_position


@pytest.mark.asyncio
async def test_get_completed_timestamp(redis_service: Redis) -> None:
    session_id = 'test_session'
    expected_timestamp = datetime.now().timestamp()
    redis_service.redis.hget = AsyncMock(return_value=expected_timestamp)

    timestamp = await redis_service.get_completed_timestamp(session_id)

    redis_service.redis.hget.assert_awaited_once_with(f'session:{session_id}', 'completed_timestamp')
    assert timestamp == expected_timestamp


# @pytest.mark.asyncio
# async def test_complete_task(redis_service: Redis, mock_datetime: Any) -> None:
#     session_id = 'test_session'
#
#     mock_dt, fixed_time = mock_datetime
#     with mock_dt:
#         await redis_service.complete_task(session_id)
#
#         pipeline = redis_service.redis.pipeline.return_value.__aenter__.return_value
#         pipeline.hset.assert_called_once_with(
#             f'session:{session_id}',
#             mapping={'status': TaskStatus.COMPLETED, 'completed_timestamp': fixed_time},
#         )
#         pipeline.lrem.assert_called_once_with('processing_queue', 1, session_id)
#         pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_storage(redis_service: Redis) -> None:
    redis_service.redis.flushdb = AsyncMock()

    await redis_service.clear_storage()

    redis_service.redis.flushdb.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_connection(redis_service: Redis) -> None:
    redis_service.redis.ping = AsyncMock()

    await redis_service.check_redis_connection()

    redis_service.redis.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_connection_error(redis_service: Redis) -> None:
    redis_service.redis.ping = AsyncMock(side_effect=ConnectionError)

    with patch('app.services.redis_service.logger') as mock_logger:
        with pytest.raises(ConnectionError):
            await redis_service.check_redis_connection()

        mock_logger.error.assert_called_once_with(
            'Error connecting to Redis server. Please check the connection settings.'
        )

import json
from typing import Any, Tuple
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.processing import send_to_queue
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
    service.create_task = AsyncMock()
    return service


@pytest.fixture
def mock_rabbit() -> Tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    with patch('aio_pika.connect_robust') as mock:
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        mock_exchange = AsyncMock()

        mock.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        mock_channel.declare_queue.return_value = mock_queue
        mock_channel.default_exchange = mock_exchange

        return mock, mock_connection, mock_channel, mock_exchange


@pytest.mark.asyncio
async def test_send_to_queue(redis_service: Redis, mock_rabbit: Any) -> None:
    message = {'session_id': 'test_session'}
    mock_connect, mock_connection, mock_channel, mock_exchange = mock_rabbit

    with patch('app.services.processing.redis_service', new=redis_service), patch(
        'app.services.processing.aio_pika.connect_robust', new=mock_connect
    ):
        await send_to_queue(message)

    # Check if the task was created in Redis
    redis_service.create_task.assert_awaited_once_with('test_session')

    # Verify RabbitMQ connection and queue declaration
    mock_connect.assert_awaited_once_with(settings.RABBITMQ_URL)
    mock_connection.channel.assert_awaited_once()
    mock_channel.declare_queue.assert_awaited_once_with('processing_queue', durable=True)

    # Verify message publication to the queue
    mock_exchange.publish.assert_awaited_once()
    call_args = mock_exchange.publish.await_args
    assert call_args is not None
    actual_message, _actual_kwargs = call_args
    expected_body = json.dumps(message).encode()
    assert actual_message[0].body == expected_body

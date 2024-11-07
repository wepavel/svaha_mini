import json
from unittest.mock import AsyncMock, patch

from aio_pika.abc import AbstractRobustConnection
import pytest

from app.app.core.config import settings
from app.app.services.processing import RQueue
from app.app.services.redis_service import Redis


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


# @pytest.fixture
# def mock_rabbit() -> Tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
#     with patch('aio_pika.connect_robust') as mock:
#         mock_connection = AsyncMock()
#         mock_channel = AsyncMock()
#         mock_queue = AsyncMock()
#         mock_exchange = AsyncMock()
#
#         mock.return_value = mock_connection
#         mock_connection.channel.return_value = mock_channel
#         mock_channel.declare_queue.return_value = mock_queue
#         mock_channel.default_exchange = mock_exchange
#
#         return mock, mock_connection, mock_channel, mock_exchange


@pytest.fixture
def mock_rabbit_connection() -> AsyncMock:
    mock_connection = AsyncMock()

    mock_connection.__aenter__.return_value = mock_connection

    return mock_connection


@pytest.fixture
def rabbit_service(mock_rabbit_connection: AsyncMock) -> RQueue:
    with patch('app.services.processing.RQueue.create_connection', return_value=mock_rabbit_connection):
        service = RQueue()
        return service


@pytest.mark.asyncio
async def test_create_connection():
    with patch('app.services.processing.aio_pika.connect_robust') as mock_connect:
        mock_connect.return_value = AsyncMock(spec=AbstractRobustConnection)
        connection = await RQueue.create_connection()
        assert connection is not None
        mock_connect.assert_awaited_once_with(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
        )


@pytest.mark.asyncio
async def test_check_rabbit_connection(rabbit_service: RQueue):
    mock_channel = AsyncMock()
    rabbit_service.connection.channel.return_value = mock_channel

    await rabbit_service.check_rabbit_connection()

    rabbit_service.connection.__aenter__.assert_awaited_once()
    rabbit_service.connection.channel.assert_awaited_once()
    rabbit_service.connection.channel.return_value.declare_queue.assert_awaited_once_with('check_queue', durable=True)


@pytest.mark.asyncio
async def test_send_to_queue(rabbit_service: RQueue, redis_service: Redis, mock_rabbit_connection: AsyncMock):
    message = {'session_id': 'test_session'}
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()
    mock_exchange = AsyncMock()

    mock_rabbit_connection.channel.return_value = mock_channel
    mock_channel.declare_queue.return_value = mock_queue
    mock_channel.default_exchange = mock_exchange

    with patch('app.services.processing.redis_service', new=redis_service):
        await rabbit_service.send_to_queue(message)

    # Check if the task was created in Redis
    redis_service.create_task.assert_awaited_once_with('test_session')

    # Verify RabbitMQ connection and queue declaration
    mock_rabbit_connection.channel.assert_awaited_once()
    mock_channel.declare_queue.assert_awaited_once_with('processing_queue', durable=True)

    # Verify message publication to the queue
    mock_exchange.publish.assert_awaited_once()
    call_args = mock_exchange.publish.await_args
    assert call_args is not None
    args, kwargs = call_args
    actual_message = args[0]  # The first argument should be the Message object
    expected_body = json.dumps(message).encode()
    assert actual_message.body == expected_body
    assert kwargs['routing_key'] == mock_queue.name


@pytest.mark.asyncio
async def test_send_to_queue_exception(rabbit_service: RQueue, redis_service: Redis, mock_rabbit_connection: AsyncMock):
    message = {'session_id': 'test_session'}
    mock_channel = AsyncMock()
    mock_channel.declare_queue.side_effect = Exception('Test exception')

    mock_rabbit_connection.channel.return_value = mock_channel

    with patch('app.services.processing.redis_service', new=redis_service), pytest.raises(
        Exception, match='Test exception'
    ):
        await rabbit_service.send_to_queue(message)

    # Check if the task was created in Redis
    redis_service.create_task.assert_awaited_once_with('test_session')

    # Verify RabbitMQ connection attempt
    mock_rabbit_connection.channel.assert_awaited_once()

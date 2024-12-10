import json
from unittest.mock import AsyncMock, MagicMock, patch

from aio_pika import Channel, Message
from aio_pika.abc import AbstractRobustConnection
import pytest

from app.core.config import settings
from app.services.processing import RQueue, r_queue
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
def mock_rabbit_connection() -> AsyncMock:
    return AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock()))


@pytest.fixture
def mock_rabbit_channel() -> AsyncMock:
    return AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock()))


class AsyncContextManagerMock(AsyncMock):
    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_connection_pool():
    pool = MagicMock()
    connection = AsyncMock()
    channel = AsyncMock(spec=Channel)
    connection.channel.return_value = channel
    pool.acquire.return_value = AsyncContextManagerMock(return_value=connection)
    return pool


@pytest.fixture
def mock_channel_pool():
    pool = MagicMock()
    channel = AsyncMock(spec=Channel)
    pool.acquire.return_value = AsyncContextManagerMock(return_value=channel)
    return pool


@pytest.fixture
def rabbit_service(mock_connection_pool, mock_channel_pool) -> RQueue:
    service = RQueue()
    service.connection_pool = mock_connection_pool
    service.channel_pool = mock_channel_pool
    return service


@pytest.mark.asyncio
async def test_get_connection():
    with patch('app.services.processing.aio_pika.connect_robust') as mock_connect:
        mock_connect.return_value = AsyncMock(spec=AbstractRobustConnection)
        connection = await RQueue.get_connection()
        assert connection is not None
        mock_connect.assert_awaited_once_with(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
        )


@pytest.mark.asyncio
async def test_get_channel(rabbit_service: RQueue):
    channel = await rabbit_service.get_channel()

    assert isinstance(channel, AsyncMock)
    # Check if the returned object has the same methods as Channel
    assert hasattr(channel, 'declare_queue')
    assert hasattr(channel, 'declare_exchange')
    assert hasattr(channel, 'publish')
    # Verify if pool and connection methods were called correctly
    rabbit_service.connection_pool.acquire.assert_called_once()
    connection = rabbit_service.connection_pool.acquire.return_value.__aenter__.return_value
    connection.channel.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_rabbit_pooled_connection(rabbit_service: RQueue):
    mock_channel = AsyncMock(spec=Channel)
    channel_context = AsyncMock()
    channel_context.__aenter__.return_value = mock_channel
    rabbit_service.channel_pool.acquire.return_value = channel_context

    # Successful scenario test
    with patch('app.services.processing.logger') as mock_logger:
        await rabbit_service.check_rabbit_pooled_connection()
        rabbit_service.channel_pool.acquire.assert_called_once()
        mock_channel.declare_queue.assert_awaited_once_with('check_queue', durable=True)
        mock_logger.info.assert_called_once_with('Successfully connected to RabbitMQ.')

    mock_channel.reset_mock()

    # Error scenario test
    mock_channel.declare_queue.side_effect = Exception('Test error')
    with patch('app.services.processing.logger') as mock_logger, pytest.raises(Exception, match='Test error'):
        await rabbit_service.check_rabbit_pooled_connection()
        mock_logger.error.assert_called_once_with('Error connecting to RabbitMQ: Test error')


@pytest.mark.asyncio
async def test_check_rabbit_connection():
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel

    # Successful scenario test
    with (
        patch('app.services.processing.r_queue.get_connection', return_value=mock_connection),
        patch('app.services.processing.logger') as mock_logger,
    ):
        await r_queue.check_rabbit_connection()
        r_queue.get_connection.assert_called_once()
        mock_connection.channel.assert_called_once()
        mock_channel.declare_queue.assert_called_once_with('check_queue', durable=True)
        mock_logger.info.assert_called_once_with('Successfully connected to RabbitMQ.')

    # Error scenario test
    mock_connection.channel.side_effect = Exception('Test error')
    with (
        patch('app.services.processing.r_queue.get_connection', return_value=mock_connection),
        patch('app.services.processing.logger') as mock_logger,
        pytest.raises(Exception, match='Test error'),
    ):
        await r_queue.check_rabbit_connection()
        mock_logger.error.assert_called_once_with('Error connecting to RabbitMQ: Test error')


@pytest.mark.asyncio
async def test_send_to_queue(rabbit_service: RQueue, redis_service: Redis):
    message = {'session_id': 'test_session'}
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.declare_queue.return_value = mock_queue
    mock_channel.default_exchange = mock_exchange

    channel_context = AsyncMock()
    channel_context.__aenter__.return_value = mock_channel
    rabbit_service.channel_pool.acquire.return_value = channel_context

    with patch('app.services.processing.redis_service', new=redis_service):
        await rabbit_service.send_to_queue(message)

    redis_service.create_task.assert_awaited_once_with('test_session')
    rabbit_service.channel_pool.acquire.assert_called_once()
    mock_channel.declare_queue.assert_awaited_once_with('processing_queue', durable=True)
    mock_exchange.publish.assert_awaited_once()
    call_args = mock_exchange.publish.await_args
    assert call_args is not None
    args, kwargs = call_args
    actual_message = args[0]
    assert isinstance(actual_message, Message)
    expected_body = json.dumps(message).encode()
    assert actual_message.body == expected_body
    assert kwargs['routing_key'] == mock_queue.name


@pytest.mark.asyncio
async def test_send_to_queue_exception(rabbit_service: RQueue, redis_service: Redis, mock_rabbit_connection: AsyncMock):
    message = {'session_id': 'test_session'}
    mock_channel = AsyncMock()
    mock_channel.declare_queue.side_effect = Exception('Test exception')

    channel_context = AsyncMock()
    channel_context.__aenter__.return_value = mock_channel
    rabbit_service.channel_pool.acquire.return_value = channel_context

    with (
        patch('app.services.processing.redis_service', new=redis_service),
        pytest.raises(Exception, match='Test exception'),
    ):
        await rabbit_service.send_to_queue(message)

    redis_service.create_task.assert_awaited_once_with('test_session')
    rabbit_service.channel_pool.acquire.assert_called_once()
    mock_channel.declare_queue.assert_awaited_once_with('processing_queue', durable=True)

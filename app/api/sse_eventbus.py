import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import aioredis
from aioredis.exceptions import RedisError

from app.core.logging import logger
from app.core.utils import generate_id
from app.schemas.events import Event
from app.schemas.events import EventData
from app.schemas.events import NotificationType
from app.schemas.events import Position
from app.services.redis_service import BaseRedis
from app.services.redis_service import redis_base


class SSEEventBus:
    def __init__(
        self, base_redis: BaseRedis, max_events_per_user: int = 100, message_lifetime: int = 3600,
    ) -> None:  # redis_url: str = "redis://localhost:6379"
        self.redis: aioredis.Redis = base_redis.get_redis()
        self.max_events_per_user = max_events_per_user
        self.message_lifetime = message_lifetime
        self.sse_connection_key = 'sse:active_connections'
        self.broadcast_channel = 'broadcast:all'
        self.broadcast_key = 'broadcast:messages'

    # async def add_connection(self, user_id: str):
    #     try:
    #         await self.redis.hincrby(self.sse_connection_key, user_id, 1)
    #     except RedisError as e:
    #         logger.error(f"Error adding connection for user {user_id}: {e}")
    async def add_connection(self, user_id: str, connection_info: dict = None):
        try:
            connection_info = connection_info or {}
            await self.redis.hset(self.sse_connection_key, user_id, json.dumps(connection_info))
        except RedisError as e:
            logger.error(f'Error adding connection for user {user_id}: {e}')

    # async def remove_connection(self, user_id: str):
    #     await self.redis.hincrby(self.sse_connection_key, user_id, -1)
    #     # Если счетчик достиг 0, удаляем запись
    #     count = await self.redis.hget(self.sse_connection_key, user_id)
    #     if count and int(count) <= 0:
    #         await self.redis.hdel(self.sse_connection_key, user_id)
    #         logger.info(f'Connection for user {user_id} removed')
    async def remove_connection(self, user_id: str):
        asyncio.create_task(self._remove_connection(user_id))
        # await asyncio.sleep(self.message_lifetime)
        # await self.redis.hdel(self.sse_connection_key, user_id)
        # try:
        #     logger.info(f'Connection for user {user_id} will be removed')
        #     await self.redis.hdel(self.sse_connection_key, user_id)
        #     logger.info(f'Connection for user {user_id} removed')
        # except RedisError as e:
        #     logger.error(f"Error removing connection for user {user_id}: {e}")

    async def _remove_connection(self, user_id: str):
        try:
            logger.info(f'Connection for user {user_id} will be removed')
            await self.redis.hdel(self.sse_connection_key, user_id)
            logger.info(f'Connection for user {user_id} removed')
        except RedisError as e:
            logger.error(f'Error removing connection for user {user_id}: {e}')

    async def close_all_connections(self):
        logger.info('Closing all connections')
        active_connections = await self.get_active_connections()
        for user_id in active_connections:
            await self.shutdown(user_id)
        await self.redis.delete(self.sse_connection_key)

    # async def get_active_connections(self) -> dict[str, int]:
    #     connections = await self.redis.hgetall(self.sse_connection_key)
    #     return {
    #         k.decode() if isinstance(k, bytes) else k:
    #             int(v.decode() if isinstance(v, bytes) else v)
    #         for k, v in connections.items()
    #     }

    # async def get_active_connections(self) -> dict[str, dict]:
    #     try:
    #         connections = await self.redis.hgetall(self.sse_connection_key)
    #         return {
    #             k.decode() if isinstance(k, bytes) else k:
    #             json.loads(v.decode() if isinstance(v, bytes) else v)
    #             for k, v in connections.items()
    #         }
    #     except RedisError as e:
    #         return {
    #             'test': {
    #                 'error': str(e),
    #             }
    #         }
    async def get_active_connections(self) -> dict[str, dict[str, Any]]:
        try:
            connections = await self.redis.hgetall(self.sse_connection_key)
            result = {}
            for k, v in connections.items():
                key = k.decode() if isinstance(k, bytes) else k
                try:
                    value = json.loads(v.decode() if isinstance(v, bytes) else v)
                    if not isinstance(value, dict):
                        value = {'value': value}
                except json.JSONDecodeError:
                    value = {'value': v.decode() if isinstance(v, bytes) else v}
                result[key] = value
            return result
        except RedisError as e:
            logger.error(f'Error getting active connections: {e}')
            return {'error': {'message': str(e)}}

    async def shutdown(self, session_id: str) -> None:
        # await self.post(user_id, Event(name="__exit__", data=EventData(user_id=user_id, message="Shutdown")))
        event = Event(
            name='__exit__',
            data=EventData(
                id=session_id,
                message='Server is shutting down. Please reconnect.',
                notification_type=NotificationType.WARNING,
                position=Position.RIGHT_TOP,
            ),
        )
        await self.post(session_id, event)

    async def broadcast(self, event: Event) -> None:
        try:
            event_json = event.model_dump_json()
            message_id = generate_id()

            async with self.redis.pipeline() as pipe:
                # Добавляем событие в List для broadcast
                await pipe.lpush(self.broadcast_key, event_json)
                # Ограничиваем количество broadcast событий
                await pipe.ltrim(self.broadcast_key, 0, self.max_events_per_user - 1)
                # Устанавливаем TTL для всего списка broadcast событий
                await pipe.expire(self.broadcast_key, self.message_lifetime)
                await pipe.publish(self.broadcast_channel, event_json)

                await pipe.execute()

            logger.info(f'Broadcast message sent: {event.name}')
            asyncio.create_task(self._delete_broadcast_message_after_delay(message_id, event_json))
        except RedisError as e:
            logger.error(f'Redis error in broadcast: {e}')

    async def _delete_broadcast_message_after_delay(self, message_id: str, event_json: str):
        await asyncio.sleep(self.message_lifetime)
        try:
            await self.redis.lrem(self.broadcast_key, 1, event_json)
            logger.info(f'Broadcast message {message_id} deleted after {self.message_lifetime} seconds')
        except RedisError as e:
            logger.error(f'Redis error in _delete_broadcast_message_after_delay: {e}')

    async def post(self, session_id: str, event: Event) -> None:
        try:
            event_key = f'event:{session_id}'
            event_json = event.model_dump_json()
            message_id = generate_id()

            async with self.redis.pipeline() as pipe:
                # Добавляем событие в List
                await pipe.lpush(event_key, event_json)
                # Ограничиваем количество событий
                await pipe.ltrim(event_key, 0, self.max_events_per_user - 1)
                # Устанавливаем TTL для всего списка событий
                await pipe.expire(event_key, self.message_lifetime)
                await pipe.publish(f'user:{session_id}', event_json)

                await pipe.execute()

            asyncio.create_task(self._delete_message_after_delay(session_id, message_id, event_json))
        except RedisError as e:
            logger.error(f'Redis error in post: {e}')

    async def _delete_message_after_delay(self, session_id: str, message_id: str, event_json: str):
        await asyncio.sleep(self.message_lifetime)
        try:
            event_key = f'event:{session_id}'
            await self.redis.lrem(event_key, 1, event_json)
            logger.info(f'Message {message_id} for user {session_id} deleted after {self.message_lifetime} seconds')
        except RedisError as e:
            logger.error(f'Redis error in _delete_message_after_delay: {e}')

    async def listen(self, session_id: str) -> AsyncGenerator[dict[str, str], None]:
        pubsub = self.redis.pubsub()
        logger.info(f'Listening for user {session_id} events')
        try:
            await pubsub.subscribe(f'user:{session_id}', self.broadcast_channel)
            # await self.add_connection(user_id)

            # Send the most recent events
            event_key = f'event:{session_id}'
            events = await self.redis.lrange(event_key, 0, -1)

            for event_json in events:
                event = Event.model_validate_json(event_json)
                yield event.as_sse_dict()

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = (
                        message['channel'].decode('utf-8')
                        if isinstance(message['channel'], bytes)
                        else message['channel']
                    )
                    event = Event.model_validate_json(message['data'])

                    if channel == self.broadcast_channel:
                        event.data.info = event.data.info or {}
                        event.data.info['broadcast'] = True

                    if event.name == '__exit__' and channel != self.broadcast_channel:
                        await pubsub.unsubscribe(f'user:{session_id}', self.broadcast_channel)
                        await pubsub.close()
                        await self.remove_connection(session_id)
                        return

                    yield event.as_sse_dict()

        except Exception as e:
            # print(f"Error in listen: {e}")
            logger.error(f'Error listening on pubsub: {e}')

        finally:
            await pubsub.unsubscribe(f'user:{session_id}', 'broadcast:all')
            await pubsub.close()
            logger.info('Pubsub closed')
            # await self.remove_connection(user_id)


event_bus = SSEEventBus(redis_base, max_events_per_user=10, message_lifetime=5)


async def payment_message(
    user_id: str,
    message: str,
    notification_type: NotificationType = NotificationType.SUCCESS,
    position: Position = Position.RIGHT_BOTTOM,
) -> None:
    event = Event(
        name='message',
        data=EventData(
            id=user_id,
            message=f'Payment was successful\n{message}',
            notification_type=notification_type,
            position=position,
        ),
    )
    await event_bus.post(user_id, event)


async def wg_msg(
    user_id: str,
    message: str,
    notification_type: NotificationType = NotificationType.SUCCESS,
    position: Position = Position.RIGHT_BOTTOM,
) -> None:
    event = Event(
        name='message',
        data=EventData(id=user_id, message=message, notification_type=notification_type, position=position),
    )
    await event_bus.post(user_id, event)


async def broadcast_msg(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    position: Position = Position.RIGHT_BOTTOM,
) -> None:
    event = Event(
        name='broadcast_message',
        data=EventData(id='broadcast', message=message, notification_type=notification_type, position=position),
    )
    await event_bus.broadcast(event)


async def set_upload_progress(
    user_id: str,
    progress: int,
    notification_type: NotificationType = NotificationType.INFO,
    position: Position = Position.RIGHT_BOTTOM,
) -> None:
    event = Event(
        name='upload_progress',
        data=EventData(id=user_id, message=str(progress), notification_type=notification_type, position=position),
    )
    await event_bus.broadcast(event)


async def set_mixing_progress(
    user_id: str,
    progress: int,
    notification_type: NotificationType = NotificationType.INFO,
    position: Position = Position.RIGHT_BOTTOM,
) -> None:
    event = Event(
        name='upload_progress',
        data=EventData(id=user_id, message=str(progress), notification_type=notification_type, position=position),
    )
    await event_bus.broadcast(event)

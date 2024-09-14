from datetime import datetime

import aioredis
import redis

from app.models.task import TaskStatus
from app.core.config import settings

# redis_host = 'localhost'
# redis_port = 6379


class Redis:
    def __init__(self):
        self.redis: aioredis.Redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )


    async def create_task(self, session_id):
        await self.redis.rpush('processing_queue', session_id)
        await self.redis.set(f'status:{session_id}', TaskStatus.QUEUED)
        await self.redis.set(f'timestamp:{session_id}', datetime.now().timestamp())

    async def get_status(self, session_id):
        return await self.redis.get(f'status:{session_id}')

    async def get_position(self, session_id):
        return await self.redis.lpos('processing_queue', session_id)

    async def get_completed_timestamp(self, session_id):
        return await self.redis.get(f'completed_timestamp:{session_id}')

    async def clear_storage(self):
        await self.redis.flushdb()


class SyncRedis:
    """
    to purge DB:
    r.flushdb()

    r.llen('mylist')

    """
    def __init__(self):
        self.redis: redis.Redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    def complete_task(self, session_id):
        self.redis.set(f'status:{session_id}', TaskStatus.COMPLETED)
        self.redis.set(f'completed_timestamp:{session_id}', datetime.now().timestamp())
        self.redis.lrem('processing_queue', 1, session_id)


redis_service = Redis()

sync_redis_service = SyncRedis()

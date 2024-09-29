from datetime import datetime

import aioredis

from app.core.config import settings
from app.models.task import TaskStatus

# redis_host = 'localhost'
# redis_port = 6379


class Redis:
    def __init__(self) -> None:
        self.redis: aioredis.Redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            username=settings.REDIS_LOGIN,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    async def create_task(self, session_id: str) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.rpush('processing_queue', session_id)
            await pipe.hset(
                f'session:{session_id}', mapping={'status': TaskStatus.QUEUED, 'timestamp': datetime.now().timestamp()}
            )
            await pipe.execute()

    async def get_status(self, session_id: str) -> str | None:
        return await self.redis.hget(f'session:{session_id}', 'status')

    async def get_position(self, session_id: str) -> str | None:
        return await self.redis.lpos('processing_queue', session_id)

    async def get_completed_timestamp(self, session_id: str) -> float | None:
        return await self.redis.hget(f'session:{session_id}', 'completed_timestamp')

    async def complete_task(self, session_id: str) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}',
                mapping={'status': TaskStatus.COMPLETED, 'completed_timestamp': str(datetime.now().timestamp())},
            )
            await pipe.lrem('processing_queue', 1, session_id)
            await pipe.execute()

    async def clear_storage(self) -> None:
        await self.redis.flushdb()


redis_service = Redis()

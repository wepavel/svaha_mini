from datetime import datetime

import aioredis

from app.core.config import settings
from app.core.logging import logger
from app.models.task import TaskStatus


class BaseRedis:
    def __init__(self) -> None:
        self.redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            username=settings.REDIS_LOGIN,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    async def check_redis_connection(self) -> None:
        try:
            await self.redis.ping()
            logger.info('Successfully connected to Redis.')
        except ConnectionError as e:
            logger.error('Error connecting to Redis server. Please check the connection settings.')
            raise e

    # async def get_status(self, session_id: str) -> str | None:
    #     return await self.redis.hget(f'session:{session_id}', 'status')
    #
    # async def get_progress(self, session_id: str) -> int | None:
    #     return await self.redis.hget(f'session:{session_id}', 'progress')
    #
    # async def get_track_id(self, session_id: str) -> str | None:
    #     return await self.redis.hget(f'session:{session_id}', 'track_id')
    #
    # async def get_position(self, session_id: str) -> str | None:
    #     return await self.redis.lpos('processing_queue', session_id)
    #
    # async def get_completed_timestamp(self, session_id: str) -> float | None:
    #     return await self.redis.hget(f'session:{session_id}', 'completed_timestamp')
    #
    # async def get_download_url(self, session_id: str) -> str | None:
    #     return await self.redis.hget(f'session:{session_id}', 'download_url')

    async def clear_storage(self) -> None:
        await self.redis.flushdb()

    def get_redis(self) -> aioredis.Redis:
        return self.redis


redis_base = BaseRedis()


class APIRedis:
    def __init__(self, redis: BaseRedis):
        self.redis = redis.get_redis()

    async def init_task(self, session_id: str) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}', mapping={'status': TaskStatus.INIT.value, 'progress': 0, 'download_url': ''}
            )
            await pipe.execute()

    async def create_task(self, session_id: str, track_id: str) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.rpush('processing_queue', session_id)
            await pipe.hset(
                f'session:{session_id}',
                mapping={
                    'track_id': track_id,
                    'progress': 0,
                    'status': TaskStatus.QUEUED.value,
                    'timestamp': datetime.now().timestamp(),
                    'download_url': '',
                },
            )
            await pipe.execute()

    async def get_session_data(
        self,
        session_id: str,
        *,
        status: bool = False,
        progress: bool = False,
        track_id: bool = False,
        position: bool = False,
        completed_timestamp: bool = False,
        download_url: bool = False,
    ) -> dict[str, str | int | float | None]:
        """
        Retrieves session data for the specified fields using Redis pipeline.

        Args:
            session_id (str): The session ID.
            status (bool, optional): Whether to retrieve the status of the session. Defaults to False.
            progress (bool, optional): Whether to retrieve the progress of the session. Defaults to False.
            track_id (bool, optional): Whether to retrieve the track ID associated with the session. Defaults to False.
            position (bool, optional): Whether to retrieve the position of the session in the processing queue. Defaults to False.
            completed_timestamp (bool, optional): Whether to retrieve the timestamp when the session was completed. Defaults to False.
            download_url (bool, optional): Whether to retrieve the download URL for the session. Defaults to False.

        Returns:
            dict[str, str | int | float | None]: A dictionary containing the requested fields and their values.
        """
        fields = []
        if status:
            fields.append('status')
        if progress:
            fields.append('progress')
        if track_id:
            fields.append('track_id')
        if position:
            fields.append('position')
        if completed_timestamp:
            fields.append('completed_timestamp')
        if download_url:
            fields.append('download_url')

        async with self.redis.pipeline() as pipe:
            for field in fields:
                if field == 'position':
                    await pipe.lpos('processing_queue', session_id)
                else:
                    await pipe.hget(f'session:{session_id}', field)

            results = await pipe.execute()

            if len(fields) == 1:
                value = results[0]
                if fields[0] == 'progress':
                    return int(value) if value is not None else None
                if fields[0] == 'completed_timestamp':
                    return float(value) if value is not None else None
                return value
            data = {}
            for field, value in zip(fields, results, strict=False):
                if field == 'progress':
                    data[field] = int(value) if value is not None else None
                elif field == 'completed_timestamp':
                    data[field] = float(value) if value is not None else None
                else:
                    data[field] = value

            return data

    async def set_status(self, session_id: str, status: TaskStatus) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}',
                mapping={'status': status.value},
            )
            await pipe.execute()

    async def set_progress(self, session_id: str, progress: int) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}',
                mapping={'progress': progress},
            )
            await pipe.execute()

    async def complete_task(self, session_id: str, download_url: str) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}',
                mapping={
                    'status': TaskStatus.COMPLETED.value,
                    'completed_timestamp': datetime.now().timestamp(),
                    'download_url': download_url,
                },
            )
            await pipe.lrem('processing_queue', 1, session_id)
            await pipe.execute()

    async def delete_task(self, session_id: str, status: TaskStatus = TaskStatus.FAILED) -> None:
        async with self.redis.pipeline() as pipe:
            await pipe.hset(
                f'session:{session_id}',
                mapping={
                    'status': status.value,
                    'completed_timestamp': datetime.now().timestamp(),
                    'download_url': None,
                },
            )
            await pipe.lrem('processing_queue', 1, session_id)
            await pipe.execute()


redis_service = APIRedis(redis_base)

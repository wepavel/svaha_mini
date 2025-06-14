import asyncio
import json

# import logging
import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool

from app.api.sse_eventbus import Position
from app.api.sse_eventbus import set_mixing_progress
from app.core.config import settings
from app.core.logging import bind_contextvars
from app.core.logging import logger
from app.schemas.task import TaskStatus
from app.services.redis_service import redis_service
from app.services.s3_async import s3


async def main() -> None:
    # clear_contextvars()
    bind_contextvars(service='consumer')
    logger.info('Consumer started')
    # logger

    async def get_connection() -> AbstractRobustConnection:
        return await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
        )

    connection_pool: Pool = Pool(get_connection, max_size=10)

    async def get_channel() -> aio_pika.Channel:
        async with connection_pool.acquire() as connection:
            return await connection.channel()

    channel_pool: Pool = Pool(get_channel, max_size=40)
    queue_name = 'processing_queue'

    async def consume() -> None:
        async with channel_pool.acquire() as channel:  # type: aio_pika.Channel
            await channel.set_qos(10)

            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False,
            )

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        # print(f'Received message: {message.body}')
                        logger.info(json.dumps(json.loads(message.body), indent=2))
                        message = json.loads(message.body)
                        try:
                            await redis_service.set_status(message['session_id'], TaskStatus.IN_PROGRESS)
                            await s3.upload_file(
                                './result.mp3',
                                f'{message["session_id"]}/{message["task_id"]}/R.mp3',
                                'svaha-mini-output',
                            )
                            track_url = (
                                f'{settings.S3_PUBLIC_DOMAIN}/{message["session_id"]}/{message["task_id"]}/R.mp3'
                            )
                            for i in range(6):
                                await set_mixing_progress(message['session_id'], int(i * 100 / 5), position=Position.CENTER)
                                await asyncio.sleep(1)

                            await redis_service.complete_task(message['session_id'], track_url)
                        except:
                            logger.error('Error uploading file from core')
                            await redis_service.delete_task(message['session_id'])

    async with connection_pool, channel_pool:
        task = asyncio.create_task(consume())
        await task


if __name__ == '__main__':
    asyncio.run(main())

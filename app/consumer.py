import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool
import aioboto3

from app.core.config import settings
from app.services.redis_service import redis_service
from app.services.s3_async import s3

# s3_target = aioboto3.resource(
#     's3',
#     endpoint_url=settings.S3_ENDPOINT,
#     aws_access_key_id=settings.S3_ACCESS_KEY,
#     aws_secret_access_key=settings.S3_SECRET_KEY,
#     aws_session_token=None,
#     config=aioboto3.session.Config(signature_version='s3v4'),
#     verify=False,
# )


async def process_message(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    async with message.process():
        print(message.body)
        message = json.loads(message.body)
        await redis_service.complete_task(message['session_id'])
        await asyncio.sleep(1)


async def main() -> None:
    async def get_connection() -> AbstractRobustConnection:
        return await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD
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
                queue_name, durable=True, auto_delete=False,
            )

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        print(message.body)
                        message = json.loads(message.body)
                        await redis_service.set_task_process(message['session_id'])
                        await asyncio.sleep(5)
                        await s3.upload_file('../result.mp3', f'{message["session_id"]}/{message["task_id"]}/R.mp3', 'svaha-mini-output')
                        track_url = await s3.get_file_url(f'{message["session_id"]}/{message["task_id"]}/R.mp3', 'svaha-mini-output')
                        await redis_service.complete_task(message['session_id'], track_url)



    async with connection_pool, channel_pool:
        task = asyncio.create_task(consume())
        await task
    # try:
    #
    #     connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    #     queue_name = 'processing_queue'
    #
    #     async with connection:
    #         # Creating channel
    #         channel = await connection.channel()
    #
    #         # Will take no more than 10 messages in advance
    #         await channel.set_qos(prefetch_count=10)
    #
    #         # Declaring queue
    #         queue = await channel.declare_queue(queue_name, durable=True, auto_delete=False)
    #
    #         # async with queue.iterator() as queue_iter:
    #         #     async for message in queue_iter:
    #         #         async with message.process():
    #         #             print(message.body)
    #         #
    #         #             if queue.name in message.body.decode():
    #         #                 break
    #         await queue.consume(process_message)
    #
            # try:
            #     # Wait until terminate
            #     await asyncio.Future()
            # finally:
            #     await connection.close()
    #
    # except Exception as e:
    #     print(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    asyncio.run(main())

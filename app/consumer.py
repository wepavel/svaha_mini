import asyncio
import json

import aio_pika
import boto3

from app.core.config import settings
from app.services.redis_service import redis_service

s3_target = boto3.resource(
    's3',
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    aws_session_token=None,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False,
)


async def process_message(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    async with message.process():
        print(message.body)
        message = json.loads(message.body)
        await redis_service.complete_task(message['session_id'])
        await asyncio.sleep(1)


async def main() -> None:
    try:

        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        queue_name = 'processing_queue'

        async with connection:
            # Creating channel
            channel = await connection.channel()

            # Will take no more than 10 messages in advance
            await channel.set_qos(prefetch_count=10)

            # Declaring queue
            queue = await channel.declare_queue(queue_name, durable=True, auto_delete=False)

            # async with queue.iterator() as queue_iter:
            #     async for message in queue_iter:
            #         async with message.process():
            #             print(message.body)
            #
            #             if queue.name in message.body.decode():
            #                 break
            await queue.consume(process_message)

            try:
                # Wait until terminate
                await asyncio.Future()
            finally:
                await connection.close()

    except Exception as e:
        print(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    asyncio.run(main())

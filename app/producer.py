import boto3
import aio_pika
from app.services.redis_service import redis_service, sync_redis_service
from app.core.config import settings
import asyncio

# s3_target = boto3.resource('s3',
#     endpoint_url='http://127.0.0.1:9001',
#     aws_access_key_id=settings.S3_ACCESS_KEY,
#     aws_secret_access_key=settings.S3_SECRET_KEY,
#     aws_session_token=None,
#     config=boto3.session.Config(signature_version='s3v4'),
#     verify=False
# )

async def process_message(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    async with message.process():
        print(message.body)
        await asyncio.sleep(1)


async def main() -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)
            # Declaring queue
            queue = await channel.declare_queue('processing_queue', auto_delete=True)

            await queue.consume(process_message)

    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
import aio_pika

from app.core.config import settings
from app.services.redis_service import redis_service


async def send_to_queue(message: dict) -> None:
    session_id = message['session_id']
    await redis_service.create_task(session_id)

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        queue = await channel.declare_queue('processing_queue', durable=True)

        await channel.default_exchange.publish(
            aio_pika.Message(body=b'Hello world'),
            # aio_pika.Message(body=bytes(json.dumps(message), 'utf-8')),
            routing_key=queue.name,
        )

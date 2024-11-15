import json

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool

from app.core.config import settings
from app.core.logging import logger
from app.services.redis_service import redis_service


class RQueue:
    def __init__(self):
        self.connection_pool = Pool(self.get_connection, max_size=10)
        self.channel_pool = Pool(self.get_channel, max_size=40)

    @staticmethod
    async def get_connection() -> AbstractRobustConnection:
        return await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
        )

    async def get_channel(self) -> aio_pika.Channel:
        async with self.connection_pool.acquire() as connection:
            return await connection.channel()

    async def check_rabbit_pooled_connection(self) -> None:
        try:
            async with self.channel_pool.acquire() as channel:
                await channel.declare_queue('check_queue', durable=True)
                logger.info('Successfully connected to RabbitMQ.')
        except Exception as e:
            logger.error(f'Error connecting to RabbitMQ: {e}')
            raise e

    @staticmethod
    async def check_rabbit_connection():
        try:
            connection = await r_queue.get_connection()
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue('check_queue', durable=True)
            logger.info('Successfully connected to RabbitMQ.')
        except Exception as e:
            logger.error(f'Error connecting to RabbitMQ: {e}')
            raise e

    async def send_to_queue(self, message: dict) -> None:
        session_id = message['session_id']
        await redis_service.create_task(session_id)

        async with self.channel_pool.acquire() as channel:
            queue = await channel.declare_queue('processing_queue', durable=True)

            await channel.default_exchange.publish(
                aio_pika.Message(body=bytes(json.dumps(message), 'utf-8')),
                routing_key=queue.name,
            )



r_queue = RQueue()

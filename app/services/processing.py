from asyncio import create_task as create_async_task, get_event_loop
import json

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.core.config import settings
from app.core.logging import logger
from app.services.redis_service import redis_service


class RQueue:
    def __init__(self):
        if get_event_loop().is_running():
            self.connection = create_async_task(self.create_connection())
        else:
            loop = get_event_loop()
            self.connection = loop.run_until_complete(self.create_connection())

    @staticmethod
    async def create_connection() -> AbstractRobustConnection:
        try:
            connection = await aio_pika.connect_robust(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                login=settings.RABBITMQ_LOGIN,
                password=settings.RABBITMQ_PASSWORD,
            )
        except Exception as e:
            logger.error(e)
        return connection

    async def check_rabbit_connection(self) -> None:
        try:
            async with self.connection as connection:
                channel = await connection.channel()
                await channel.declare_queue('check_queue', durable=True)
            # print("Подключение к RabbitMQ успешно.")
            logger.info('Successfully connected to RabbitMQ.')
        except Exception as e:
            # print(f"Ошибка подключения к RabbitMQ: {e}")
            logger.error(f'Error connecting to RabbitMQ: {e}')

    async def send_to_queue(self, message: dict) -> None:
        session_id = message['session_id']
        await redis_service.create_task(session_id)

        async with self.connection as connection:
            channel = await connection.channel()

            queue = await channel.declare_queue('processing_queue', durable=True)

            await channel.default_exchange.publish(
                aio_pika.Message(body=bytes(json.dumps(message), 'utf-8')),
                routing_key=queue.name,
            )


r_queue = RQueue()

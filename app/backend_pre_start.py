import asyncio
import logging

from tenacity import after_log
from tenacity import before_log
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from app.core.config import settings
from app.core.logging import logger
from app.services.processing import r_queue
from app.services.redis_service import redis_base as redis_service
from app.services.s3_async import s3

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARNING),
)
async def init_redis() -> None:
    await redis_service.check_redis_connection()


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARNING),
)
async def init_rabbit() -> None:
    await r_queue.check_rabbit_connection()


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARNING),
)
async def init_s3() -> None:
    await s3.check_s3_connection(settings.S3_SVAHA_READ_BUCKET)


async def main() -> None:
    logger.info('Initializing services')
    await init_redis()
    await init_rabbit()
    await init_s3()
    logger.info('Services finished initializing')


if __name__ == '__main__':
    asyncio.run(main())

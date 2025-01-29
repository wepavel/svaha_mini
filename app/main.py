import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.sse_eventbus import event_bus
from app.core.config import settings
from app.core.exceptions import exception_handler
from app.core.logging import UvicornAccessLogFormatter
from app.core.logging import UvicornCommonLogFormatter
from app.core.openapi import custom_openapi


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:

    level = settings.LOG_LEVEL

    uvicorn_logger = logging.getLogger('uvicorn')
    uvicorn_logger.setLevel(level)
    uvicorn_logger.handlers[0].setFormatter(UvicornCommonLogFormatter())

    access_logger = logging.getLogger('uvicorn.access')
    access_logger.setLevel(level)
    access_logger.handlers[0].setFormatter(UvicornAccessLogFormatter())

    yield

    await event_bus.close_all_connections()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    # openapi_url=f'{settings.API_V1_STR}/openapi.json',
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
    # root_path=settings.API_V1_STR
    # prefix=settings.API_V1_STR,
    docs_url='/docs',
    # openapi_url="/openapi.json",
    # static_url="/static"
)


custom_openapi(app)
exception_handler(app)
# app.add_middleware(RequestIDMiddleware)

# for origin in settings.BACKEND_CORS_ORIGINS: print(str(origin).rstrip('/'))


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == '__main__':
    uvicorn.run(
        app,
        host=str(settings.HOST),
        port=settings.PORT,
        # log_config='./log_config.json',
    )  # ,log_config='./app/log_config.json'

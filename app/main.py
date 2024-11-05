from multiprocessing import cpu_count

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.core.exceptions import exception_handler
from app.core.openapi import custom_openapi

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
)

custom_openapi(app)
exception_handler(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip('/') for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)


def get_worker_count() -> int:
    return cpu_count()


if __name__ == '__main__':
    worker_count = get_worker_count()
    uvicorn.run(app, host=str(settings.HOST), port=settings.PORT, log_config='./app/log_config.json')

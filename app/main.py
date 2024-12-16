
from fastapi import FastAPI
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.core.exceptions import exception_handler
from app.core.openapi import custom_openapi
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title=settings.PROJECT_NAME,
    # openapi_url=f'{settings.API_V1_STR}/openapi.json',
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
    # root_path=settings.API_V1_STR
    # prefix=settings.API_V1_STR,
    docs_url=f'/docs',
    # openapi_url="/openapi.json",
    # static_url="/static"
)

custom_openapi(app)
exception_handler(app)


# for origin in settings.BACKEND_CORS_ORIGINS: print(str(origin).rstrip('/'))


app.add_middleware(
    CORSMiddleware,
    # allow_origins=[str(origin).rstrip('/') for origin in settings.BACKEND_CORS_ORIGINS],
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
        log_config='./log_config.json',
    )  # ,log_config='./app/log_config.json'

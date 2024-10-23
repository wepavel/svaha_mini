import uvicorn
from fastapi import FastAPI

# from fastapi.openapi.utils import get_openapi
from app.api import api_router
from app.core.config import settings
from app.core.openapi import custom_openapi
from app.core.exceptions import exception_handler

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
)

custom_openapi(app)

# exception_handler(app)
# exception_handler1(app)
exception_handler(app)

# app.add_exception_handler(RequestValidationError, validation_exception_handler)
# exception_handler2(app)
# exception_handler3(app)
# exception_handler(app)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
#     allow_credentials=True,
#     allow_methods=['*'],
#     allow_headers=['*']
# )

app.include_router(api_router)

if __name__ == '__main__':
    uvicorn.run(app, host=str(settings.HOST), port=settings.PORT)

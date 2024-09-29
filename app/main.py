
import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api import api_router
from app.core.config import settings
from app.core.errors import exception_handler


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title='Custom API',
        version='1.0.0',
        description='This is a custom OpenAPI schema',
        routes=app.routes,
    )
    # openapi_schema["components"]["schemas"]["HTTPException"] = {
    #     "type": "object",
    #     "properties": {
    #         "message": {"type": "string"},
    #         "type": {"type": "string"}
    #     }
    # }
    openapi_schema['components']['schemas']['HTTPException'] = {
        'type': 'object',
        'properties': {
            'msg': {'type': 'string'},
            'code': {'type': 'integer'},
            'details': {'type': 'array', 'items': {'type': 'object'}},
        },
    }
    openapi_schema['components']['schemas']['ValidationError'] = {
        'type': 'object',
        'properties': {
            'msg': {'type': 'string'},
            'code': {'type': 'integer'},
            'details': {'type': 'array', 'items': {'type': 'object'}},
        },
    }
    for path in openapi_schema['paths']:
        for method in openapi_schema['paths'][path]:
            responses = openapi_schema['paths'][path][method]['responses']
            if '422' in openapi_schema['paths'][path][method]['responses']:
                del openapi_schema['paths'][path][method]['responses']['422']
            responses['400'] = {
                'description': 'Validation Error',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ValidationError'}}},
            }
            responses['500'] = {
                'description': 'Internal Server Error',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/HTTPException'}}},
            }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
)

app.openapi = custom_openapi

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

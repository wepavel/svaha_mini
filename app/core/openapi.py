from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title='Svaha Mini docs',
            version='1.0.0',
            description='This is an OpenAPI schema for Svaha Mini',
            routes=app.routes,
        )
        openapi_schema['components']['schemas']['ValidationError'] = {
            'type': 'object',
            'properties': {
                'msg': {'type': 'string'},
                'code': {'type': 'integer', 'default': 4000},
                'details': {'type': 'object'},
                'redirect': {'type': 'boolean', 'default': False},
                'notification': {'type': 'boolean', 'default': False},
            },
        }
        openapi_schema['components']['schemas']['HTTPException'] = {
            'type': 'object',
            'properties': {
                'msg': {'type': 'string'},
                'code': {'type': 'integer', 'default': 5000},
                'details': {'type': 'object'},
                'redirect': {'type': 'boolean', 'default': False},
                'notification': {'type': 'boolean', 'default': False},
            },
        }
        for path in openapi_schema['paths']:
            for method in openapi_schema['paths'][path]:
                responses = openapi_schema['paths'][path][method]['responses']
                if '422' in openapi_schema['paths'][path][method]['responses']:
                    del openapi_schema['paths'][path][method]['responses']['422']
                responses['400'] = {
                    'description': 'Bad Request',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ValidationError'}}},
                }
                responses['500'] = {
                    'description': 'Internal Server Error',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/HTTPException'}}},
                }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

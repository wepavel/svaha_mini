import json
from enum import Enum
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


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


class ErrorCodes(Enum):
    IncorrCreds = 1
    NotAuthenticated = 2
    Unauthorized = 3
    Forbidden = 4
    ExpiredSignatureError = 5
    ValidationError = 6
    UserExists = 7
    UserNotExists = 8
    NotEnoughPriv = 9
    NotEnoughPerm = 10
    NotFound = 11
    InternalError = 12
    DbError = 13


ERROR_CODES_MAP: dict[ErrorCodes, dict[str, Any]] = {
    ErrorCodes.IncorrCreds: {'code': 4000, 'msg': 'Incorrect login or password'},
    ErrorCodes.Unauthorized: {
        'code': 4001,
        'msg': 'Sorry, you are not allowed to access this service: UnauthorizedRequest',
    },
    ErrorCodes.Forbidden: {'code': 4003, 'msg': 'Request failed due to insufficient permissions: ForbiddenRequest'},
    ErrorCodes.UserNotExists: {'code': 4004, 'msg': 'The user does not exist in the system'},
    ErrorCodes.NotAuthenticated: {'code': 4007, 'msg': 'Not authenticated'},
    ErrorCodes.ExpiredSignatureError: {'code': 4009, 'msg': 'Could not validate credentials: ExpiredSignatureError'},
    ErrorCodes.ValidationError: {'code': 4010, 'msg': 'Could not validate credentials: ValidationError'},
    ErrorCodes.UserExists: {'code': 4095, 'msg': 'The user already exists in the system'},
    ErrorCodes.NotEnoughPriv: {'code': 4101, 'msg': "The user doesn't have enough privileges"},
    ErrorCodes.NotEnoughPerm: {'code': 4102, 'msg': 'Not enough permissions'},
    ErrorCodes.NotFound: {'code': 4104, 'msg': 'Not Found'},
    ErrorCodes.InternalError: {'code': 5000, 'msg': 'Internal Server Error'},
    ErrorCodes.DbError: {'code': 5002, 'msg': 'Bad Gateway'},
}

HTTP_2_CUSTOM_ERR: dict[int, ErrorCodes] = {422: ErrorCodes.ValidationError}


class EXC(HTTPException):
    def __init__(
        self,
        exc: ErrorCodes,
        details: dict = {},
        redirect: bool = False,
        notification: bool = False,
        headers: dict | None = None,
    ) -> None:

        code = ERROR_CODES_MAP.get(exc).get('code', 5999)
        msg = ERROR_CODES_MAP.get(exc).get('msg', 'An error occurred')

        message = {
            'code': code,
            'msg': msg,
            'details': details,
            'redirect': redirect,
            'notification': notification,
            'custom': True,
        }
        if headers:
            message['headers'] = headers

        super().__init__(status_code=400, detail=json.dumps(message), headers=headers)


def exception_handler(app: FastAPI) -> None:
    def create_error_response(msg: str, code: int, details: dict) -> JSONResponse:
        redirect = details.get('redirect', False)
        notification = details.get('notification', False)
        details.pop('redirect', None), details.pop('notification', None)

        if details.get('custom', False):
            inner_code = details.get('code')
            details.pop('code', None), details.pop('custom', None)
        elif code in HTTP_2_CUSTOM_ERR:
            err = ERROR_CODES_MAP.get(HTTP_2_CUSTOM_ERR.get(code, ErrorCodes.InternalError))
            inner_code = err.get('code', 5999)
            msg = err.get('msg', 'An error occurred')
        else:
            inner_code = 5999

        code = 400 if 4000 <= inner_code < 5000 else 500

        return JSONResponse(
            status_code=code,
            content=jsonable_encoder(
                {'msg': msg, 'code': inner_code, 'details': details, 'redirect': redirect, 'notification': notification}
            ),
        )

    def parse_error_detail(detail: str | dict) -> dict:
        if isinstance(detail, str):
            try:
                error = json.loads(detail)
            except json.JSONDecodeError:
                error = detail
        else:
            error = detail

        if not isinstance(error, dict):
            error = {'msg': error, 'notification': False, 'redirect': False}
        return error

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        error = parse_error_detail(exc.detail)
        details = {
            'code': error.get('code', None),
            'custom': error.get('custom', False),
            'endpoint': request.url.path,
            'notification': error.get('notification', False),
            'redirect': error.get('redirect', False),
        }
        return create_error_response(error.get('msg', 'An error occurred'), exc.status_code, details)

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        errors = parse_error_detail(exc.detail)
        details = {
            'endpoint': request.url.path,
            'notification': errors.get('notification', False),
            'redirect': errors.get('redirect', False),
        }
        return create_error_response(errors.get('msg', 'An error occurred'), exc.status_code, details)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = {
            'endpoint': request.url.path,
            'errors': exc.errors()[0],
            'notification': False,
            'redirect': False,
        }
        return create_error_response('Validation Error', 422, details)

import json
from enum import Enum
from typing import Dict

from fastapi import FastAPI
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


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


ERROR_CODES_MAP: Dict[ErrorCodes, Dict[str, str | int]] = {
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
    ErrorCodes.DbError: {'code': 5002, 'msg': 'Bad Gateway'},
}

HTTP_2_CUSTOM_ERR: Dict[int, Dict[str, str | int]] = {}


class EXC(HTTPException):
    def __init__(
        self, exc: ErrorCodes, redirect: bool = False, notification: bool = False, headers: dict | None = None
    ) -> None:
        if exc not in ERROR_CODES_MAP:
            message = {'code': 5000, 'msg': 'Internal Error', 'redirect': False, 'notification': False}
        else:
            message = {
                'code': ERROR_CODES_MAP.get(exc).get('code'),
                'msg': ERROR_CODES_MAP.get(exc).get('msg'),
                'redirect': redirect,
                'notification': notification,
            }
        if headers:
            message['headers'] = headers

        status_code = ERROR_CODES_MAP.get(exc).get('code')
        exc_code = 400 if 4000 <= status_code < 5000 else 500

        super().__init__(status_code=exc_code, detail=json.dumps(message), headers=headers)


def exception_handler(app: FastAPI) -> None:
    def create_error_response(msg: str, code: int, details: dict) -> JSONResponse:

        redirect, notification = details.get('redirect', False), details.get('notification', False)
        details.pop('redirect', None), details.pop('notification', None)

        if code in HTTP_2_CUSTOM_ERR:
            msg = HTTP_2_CUSTOM_ERR.get(code).get('msg', 'An error occurred')
            code = HTTP_2_CUSTOM_ERR.get(code).get('code', 500)

        return JSONResponse(
            status_code=code,
            content=jsonable_encoder(
                {'msg': msg, 'code': code, 'details': details, 'redirect': redirect, 'notification': notification}
            ),
        )

    def parse_error_detail(detail: str | dict) -> dict:
        if isinstance(detail, str):
            try:
                errors = json.loads(detail)
            except json.JSONDecodeError:
                errors = detail
        else:
            errors = detail

        if not isinstance(errors, dict):
            errors = {'msg': errors, 'notification': False, 'redirect': False}
        return errors

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        errors = parse_error_detail(exc.detail)
        details = {
            'endpoint': request.url.path,
            'notification': errors.get('notification', False),
            'redirect': errors.get('redirect', False),
        }
        return create_error_response(errors.get('msg', 'An error occurred'), exc.status_code, details)

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
            'errors': exc.errors(),
            'notification': False,
            'redirect': False,
        }
        return create_error_response('Validation Error', 422, details)

# from enum import Enum
# import json
# from typing import Any
#
# from fastapi import FastAPI, Request
# from fastapi.encoders import jsonable_encoder
# from fastapi.exceptions import HTTPException, RequestValidationError
# from fastapi.responses import JSONResponse
# from starlette.exceptions import HTTPException as StarletteHTTPException
#
#
# class ErrorCodes(Enum):
#     #  4000: Bad Request
#     BadRequest = 4000
#     #  4021 - 4040: User Management Errors
#     CouldNotValidateUserCreds = 4021
#     UserExpiredSignatureError = 4022
#     IncorrUserCreds = 4023
#     NotAuthenticated = 4030
#     InactiveUser = 4032
#     UserRegistrationForbidden = 4033
#     UserNotExists = 4035
#     UserExists = 4036
#     #  4041 - 4060: Project Management Errors
#     ProjectLocked = 4041
#     AvailableProjectsLimitExceeded = 4042
#     AvailableEditsLimitExceeded = 4043
#     NameAlreadyExists = 4044
#     InstrumentalTrackExists = 4045
#     #  4061 - 4081: Task Management Errors
#     TaskNotFound = 4061
#     TaskAlreadyExists = 4062
#     SessionNotFound = 4071
#     SessionAlreadyExists = 4072
#     #  4301 - 4320: Resource and Limit Errors
#     TooManyRequestsError = 4301
#     #  4400: Validation Error
#     ValidationError = 4400
#     #  4401-4500: General Validation Errors
#     WrongFormat = 4411
#     #  4501 - 4508: API and Request Errors
#     Unauthorized = 4501
#     AuthorizeError = 4502
#     ForbiddenError = 4503
#     NotFoundError = 4504
#     ResponseProcessingError = 4505
#     YookassaApiError = 4511
#     #  5000: Internal Server Error
#     InternalError = 5000
#     #  5021-5040: Core Errors
#     CoreOffline = 5021
#     CoreFileUploadingError = 5022
#     #  5041-5060: Database Errors
#     DbError = 5041
#     #  5061 - 5999: System and Server Errors
#
#
# ERROR_CODES_MAP: dict[ErrorCodes, dict[str, Any]] = {
#     ErrorCodes.BadRequest: {'code': 4000, 'msg': 'Bad Request'},
#     ErrorCodes.CouldNotValidateUserCreds: {'code': 4021, 'msg': 'Could not validate credentials: ValidationError'},
#     ErrorCodes.UserExpiredSignatureError: {
#         'code': 4022,
#         'msg': 'Could not validate credentials: ExpiredSignatureError',
#     },
#     ErrorCodes.IncorrUserCreds: {'code': 4023, 'msg': 'Incorrect login or password'},
#     ErrorCodes.NotAuthenticated: {'code': 4030, 'msg': 'Not authenticated'},
#     ErrorCodes.InactiveUser: {'code': 4032, 'msg': 'Inactive user'},
#     ErrorCodes.UserRegistrationForbidden: {'code': 4033, 'msg': 'Open user registration is forbidden on this server'},
#     ErrorCodes.UserNotExists: {'code': 4035, 'msg': 'The user with this username does not exist in the system'},
#     ErrorCodes.UserExists: {'code': 4036, 'msg': 'The user already exists in the system'},
#     ErrorCodes.ProjectLocked: {'code': 4041, 'msg': 'Project locked'},
#     ErrorCodes.AvailableProjectsLimitExceeded: {'code': 4042, 'msg': 'Available projects limit exceeded'},
#     ErrorCodes.AvailableEditsLimitExceeded: {'code': 4043, 'msg': 'Available edits limit exceeded'},
#     ErrorCodes.NameAlreadyExists: {'code': 4044, 'msg': 'This name already exists'},
#     ErrorCodes.InstrumentalTrackExists: {'code': 4045, 'msg': 'Instrumental track already exists'},
#     ErrorCodes.TaskNotFound: {'code': 4061, 'msg': 'Task not found'},
#     ErrorCodes.TaskAlreadyExists: {'code': 4062, 'msg': 'Task already exists'},
#     ErrorCodes.SessionNotFound: {'code': 4071, 'msg': 'Session not found'},
#     ErrorCodes.SessionAlreadyExists: {'code': 4072, 'msg': 'Session already exists'},
#     ErrorCodes.TooManyRequestsError: {'code': 4301, 'msg': 'Too Many Requests'},
#     ErrorCodes.ValidationError: {'code': 4400, 'msg': 'Validation error'},
#     ErrorCodes.WrongFormat: {'code': 4411, 'msg': 'Wrong format'},
#     ErrorCodes.Unauthorized: {
#         'code': 4501,
#         'msg': 'Sorry, you are not allowed to access this service: UnauthorizedRequest',
#     },
#     ErrorCodes.AuthorizeError: {'code': 4502, 'msg': 'Authorization error'},
#     ErrorCodes.ForbiddenError: {'code': 4503, 'msg': 'Forbidden'},
#     ErrorCodes.NotFoundError: {'code': 4504, 'msg': 'Not Found'},
#     ErrorCodes.ResponseProcessingError: {'code': 4505, 'msg': 'Response Processing Error'},
#     ErrorCodes.YookassaApiError: {'code': 4511, 'msg': 'Yookassa Api Error'},
#     ErrorCodes.InternalError: {'code': 5000, 'msg': 'Internal Server Error'},
#     ErrorCodes.CoreOffline: {'code': 5021, 'msg': 'Core is offline'},
#     ErrorCodes.CoreFileUploadingError: {'code': 5022, 'msg': 'Core file uploading error'},
#     ErrorCodes.DbError: {'code': 5022, 'msg': 'Bad Gateway'},
# }
#
# HTTP_2_CUSTOM_ERR: dict[int, ErrorCodes] = {422: ErrorCodes.ValidationError}
#
#
# class EXC(HTTPException):
#     def __init__(
#         self,
#         exc: ErrorCodes,
#         details: dict = {},
#         redirect: bool = False,
#         notification: bool = False,
#         headers: dict | None = None,
#     ) -> None:
#
#         code = ERROR_CODES_MAP.get(exc).get('code', 5999)
#         msg = ERROR_CODES_MAP.get(exc).get('msg', 'An error occurred')
#
#         message = {
#             'code': code,
#             'msg': msg,
#             'details': details,
#             'redirect': redirect,
#             'notification': notification,
#             'custom': True,
#         }
#         if headers:
#             message['headers'] = headers
#
#         super().__init__(status_code=400, detail=json.dumps(message), headers=headers)
#
#
# def exception_handler(app: FastAPI) -> None:
#     def create_error_response(msg: str, code: int, details: dict) -> JSONResponse:
#         redirect = details.get('redirect', False)
#         notification = details.get('notification', False)
#         details.pop('redirect', None), details.pop('notification', None)
#         if details.get('reason') is None:
#             details.pop('reason', None)
#
#         if details.get('custom', False):
#             inner_code = details.get('code')
#             details.pop('code', None), details.pop('custom', None)
#         elif code in HTTP_2_CUSTOM_ERR:
#             err = ERROR_CODES_MAP.get(HTTP_2_CUSTOM_ERR.get(code, ErrorCodes.InternalError))
#             inner_code = err.get('code', 5999)
#             msg = err.get('msg', 'An error occurred')
#         else:
#             inner_code = 5999
#
#         code = 400 if 4000 <= inner_code < 5000 else 500
#
#         return JSONResponse(
#             status_code=code,
#             content=jsonable_encoder(
#                 {'msg': msg, 'code': inner_code, 'details': details, 'redirect': redirect, 'notification': notification}
#             ),
#         )
#
#     def parse_error_detail(detail: str | dict) -> dict:
#         if isinstance(detail, str):
#             try:
#                 error = json.loads(detail)
#             except json.JSONDecodeError:
#                 error = detail
#         else:
#             error = detail
#
#         if not isinstance(error, dict):
#             error = {'msg': error, 'notification': False, 'redirect': False}
#         return error
#
#     @app.exception_handler(HTTPException)
#     async def http_exception_handler(request: Request, exc: HTTPException):
#         error = parse_error_detail(exc.detail)
#         details = {
#             'code': error.get('code', None),
#             'custom': error.get('custom', False),
#             'endpoint': request.url.path,
#             'notification': error.get('notification', False),
#             'redirect': error.get('redirect', False),
#             'reason': error.get('details', {}).get('reason', None),
#         }
#         return create_error_response(error.get('msg', 'An error occurred'), exc.status_code, details)
#
#     @app.exception_handler(StarletteHTTPException)
#     async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
#         errors = parse_error_detail(exc.detail)
#         details = {
#             'endpoint': request.url.path,
#             'notification': errors.get('notification', False),
#             'redirect': errors.get('redirect', False),
#         }
#         return create_error_response(errors.get('msg', 'An error occurred'), exc.status_code, details)
#
#     @app.exception_handler(RequestValidationError)
#     async def validation_exception_handler(request: Request, exc: RequestValidationError):
#         details = {
#             'endpoint': request.url.path,
#             'errors': exc.errors()[0],
#             'notification': False,
#             'redirect': False,
#         }
#         return create_error_response('Validation Error', 422, details)


from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
import json


class ErrorResponse(BaseModel):
    code: int
    msg: str
    details: dict[str, Any] = Field(default_factory=dict)
    redirect: bool = False
    notification: bool = False
    custom: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.model_fields}

class ErrorCode(Enum):
    #  4000: Bad Request
    BadRequest = ErrorResponse(code=4000, msg="Bad Request")
    #  4021 - 4040: User Management Errors
    CouldNotValidateUserCreds = ErrorResponse(code=4021, msg="Could not validate credentials: ValidationError")
    UserExpiredSignatureError = ErrorResponse(code=4022, msg="Could not validate credentials: ExpiredSignatureError")
    IncorrUserCreds = ErrorResponse(code=4023, msg="Incorrect login or password")
    NotAuthenticated = ErrorResponse(code=4030, msg="Not authenticated")
    InactiveUser = ErrorResponse(code=4032, msg="Inactive user")
    UserRegistrationForbidden = ErrorResponse(code=4033, msg="Open user registration is forbidden on this server")
    UserNotExists = ErrorResponse(code=4035, msg="The user with this username does not exist in the system")
    UserExists = ErrorResponse(code=4036, msg="The user already exists in the system")
    #  4041 - 4060: Project Management Errors
    ProjectLocked = ErrorResponse(code=4041, msg="Project locked")
    AvailableProjectsLimitExceeded = ErrorResponse(code=4042, msg="Available projects limit exceeded")
    AvailableEditsLimitExceeded = ErrorResponse(code=4043, msg="Available edits limit exceeded")
    NameAlreadyExists = ErrorResponse(code=4044, msg="This name already exists")
    InstrumentalTrackExists = ErrorResponse(code=4045, msg="Instrumental track already exists")
    #  4061 - 4081: Task Management Errors
    TaskNotFound = ErrorResponse(code=4061, msg="Task not found")
    TaskAlreadyExists = ErrorResponse(code=4062, msg="Task already exists")
    SessionNotFound = ErrorResponse(code=4071, msg="Session not found")
    SessionAlreadyExists = ErrorResponse(code=4072, msg="Session already exists")
    #  4301 - 4320: Resource and Limit Errors
    TooManyRequestsError = ErrorResponse(code=4301, msg="Too Many Requests")
    #  4400: Validation Error
    ValidationError = ErrorResponse(code=4400, msg="Validation error")
    #  4401-4500: General Validation Errors
    WrongFormat = ErrorResponse(code=4411, msg="Wrong format")
    #  4501 - 4508: API and Request Errors
    Unauthorized = ErrorResponse(code=4501,
                                 msg="Sorry, you are not allowed to access this service: UnauthorizedRequest")
    AuthorizeError = ErrorResponse(code=4502, msg="Authorization error")
    ForbiddenError = ErrorResponse(code=4503, msg="Forbidden")
    NotFoundError = ErrorResponse(code=4504, msg="Not Found")
    ResponseProcessingError = ErrorResponse(code=4505, msg="Response Processing Error")
    YookassaApiError = ErrorResponse(code=4511, msg="Yookassa Api Error")
    #  5000: Internal Server Error
    InternalError = ErrorResponse(code=5000, msg="Internal Server Error")
    CoreOffline = ErrorResponse(code=5021, msg="Core is offline")
    CoreFileUploadingError = ErrorResponse(code=5022, msg="Core file uploading error")
    #  5041-5060: Database Errors
    DbError = ErrorResponse(code=5041, msg="Bad Gateway")
    #  5061 - 5999: System and Server Errors

    def as_dict(self) -> dict[str, Any]:
        return self.value.as_dict()

HTTP_2_CUSTOM_ERR: dict[int, ErrorResponse] = {
    422: ErrorResponse(code=4400, msg="Validation error", custom=False),
}

class EXC(HTTPException):
    def __init__(
        self,
        exc: ErrorCode,
        details: Dict[str, Any] = {},
        redirect: bool = False,
        notification: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:

        error_response = exc.value.model_copy(update={
            'details': details,
            'redirect': redirect,
            'notification': notification
        })

        super().__init__(status_code=400, detail=error_response.model_dump_json(), headers=headers)


def exception_handler(app: FastAPI) -> None:
    def create_error_response(error_response: ErrorResponse) -> JSONResponse:
        details = error_response.details.copy()
        redirect = details.pop('redirect', error_response.redirect)
        notification = details.pop('notification', error_response.notification)

        if details.get('reason') is None:
            details.pop('reason', None)

        if error_response.custom:
            inner_code = error_response.code
        elif error_response.code in HTTP_2_CUSTOM_ERR:
            custom_error = HTTP_2_CUSTOM_ERR[error_response.code]
            inner_code = custom_error.code
            error_response.msg = custom_error.msg
        else:
            inner_code = 5999

        status_code = 400 if 4000 <= inner_code < 5000 else 500

        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder({
                'msg': error_response.msg,
                'code': inner_code,
                'details': details,
                'redirect': redirect,
                'notification': notification
            }),
        )

    def parse_error_detail(detail: str | dict) -> ErrorResponse:
        if isinstance(detail, str):
            try:
                error_dict = json.loads(detail)
            except json.JSONDecodeError:
                error_dict = {"msg": detail, "code": 5000, "custom": False}
        else:
            error_dict = detail

        return ErrorResponse(**error_dict)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error = ErrorCode.ValidationError.value
        error.details = {
                'endpoint': request.url.path,
                'errors': exc.errors(),
        }
        return create_error_response(error)
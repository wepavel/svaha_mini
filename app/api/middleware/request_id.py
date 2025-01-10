from contextvars import ContextVar

import structlog
import ulid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

event_id: ContextVar[str] = ContextVar('request_id', default='')


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        structlog.contextvars.clear_contextvars()

        x_request_id = request.headers.get('X-Request-Id')
        _id = x_request_id if x_request_id else ulid.new().str

        structlog.contextvars.bind_contextvars(request_id=_id)
        event_id.set(_id)
        response = await call_next(request)
        response.headers['X-Request-Id'] = event_id.get()
        return response
